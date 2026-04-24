from __future__ import annotations

from datetime import datetime, timezone
from time import perf_counter
from typing import Any

from langgraph.graph import END, START, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import RewriteTask, TaskIteration
from app.services.detectors import BaseDetector, DetectorResult
from app.services.external_skill_rules import ExternalSkillRulesLoader
from app.services.llm_rewriter import LLMRewriter
from app.services.prompt_manager import PromptManager, PromptSpec
from app.services.system_settings import SystemSettingsService
from app.services.task_log import add_task_log


class RewriteAgent:
    def __init__(
        self,
        prompt_manager: PromptManager,
        llm_rewriter: LLMRewriter,
        detector: BaseDetector,
        external_rules_loader: ExternalSkillRulesLoader | None = None,
        system_settings_service: SystemSettingsService | None = None,
    ):
        self.prompt_manager = prompt_manager
        self.llm_rewriter = llm_rewriter
        self.detector = detector
        self.external_rules_loader = external_rules_loader
        self.system_settings_service = system_settings_service

    async def get_runtime_settings(self, session: AsyncSession):
        service = self.system_settings_service
        if service is None:
            service = SystemSettingsService(self.llm_rewriter.settings)
        return await service.get_runtime_settings(session, self.prompt_manager)

    async def run_task(self, session: AsyncSession, task: RewriteTask) -> None:
        runtime_settings = await self.get_runtime_settings(session)
        default_style = runtime_settings.default_style
        llm_mode = self.llm_rewriter.resolve_llm_mode(runtime_settings)
        await add_task_log(
            session,
            task_id=task.id,
            stage="agent",
            level="info",
            message="开始执行改写闭环。",
            detail={
                "style": task.style,
                "target_score": task.target_score,
                "max_rounds": task.max_rounds,
                "llm_mode": llm_mode,
                "llm_model": runtime_settings.openai_model,
            },
        )
        style_instruction = ""
        try:
            style_prompt = self.prompt_manager.get_prompt("style", task.style)
            style_instruction = style_prompt.instruction
        except KeyError:
            try:
                style_prompt = self.prompt_manager.get_prompt("style", default_style)
                style_instruction = style_prompt.instruction
            except KeyError:
                try:
                    style_prompt = self.prompt_manager.get_prompt("style", "deai_external")
                    style_instruction = style_prompt.instruction
                except KeyError:
                    style_instruction = ""

        if self._should_apply_external_rules(task.style):
            style_instruction = self._inject_external_rules(style_instruction)

        async def load_prompt(state: dict[str, Any]) -> dict[str, Any]:
            prompt_name = str(state["style"])
            try:
                rewrite_prompt = self.prompt_manager.get_prompt("rewrite", prompt_name)
            except KeyError:
                try:
                    rewrite_prompt = self.prompt_manager.get_prompt("rewrite", default_style)
                except KeyError:
                    rewrite_prompt = self.prompt_manager.get_prompt("rewrite", "deai_external")

            return {
                **state,
                "prompt_name": rewrite_prompt.name,
                "prompt_version": rewrite_prompt.version,
                "rewrite_prompt": rewrite_prompt,
            }

        async def rewrite_with_llm(state: dict[str, Any]) -> dict[str, Any]:
            start = perf_counter()
            candidate_text = await self.llm_rewriter.rewrite(
                rewrite_prompt=state["rewrite_prompt"],
                runtime_settings=runtime_settings,
                style_instruction=style_instruction,
                original_text=state["input_text"],
                previous_text=state["current_text"],
                round_index=state["round_index"],
            )
            latency_ms = int((perf_counter() - start) * 1000)
            return {
                **state,
                "candidate_text": candidate_text,
                "latency_ms": max(latency_ms, 1),
            }

        async def detect_score(state: dict[str, Any]) -> dict[str, Any]:
            detector_result = await self.detector.detect(state["candidate_text"])
            return {**state, "detector_result": detector_result}

        async def decide_next(state: dict[str, Any]) -> dict[str, Any]:
            detector_result: DetectorResult = state["detector_result"]

            best_score = float(state["best_score"])
            best_text = str(state["best_text"])

            if detector_result.score < best_score or not best_text:
                best_score = detector_result.score
                best_text = state["candidate_text"]

            met_target = detector_result.score <= float(state["target_score"])
            is_last_round = int(state["round_index"]) >= int(state["max_rounds"])
            done = bool(met_target or is_last_round)

            payload: dict[str, Any] = {
                **state,
                "best_score": best_score,
                "best_text": best_text,
                "met_target": met_target,
                "done": done,
            }
            if not done:
                payload["next_round_index"] = int(state["round_index"]) + 1
                payload["next_text"] = state["candidate_text"]

            return payload

        async def persist_iteration(state: dict[str, Any]) -> dict[str, Any]:
            detector_result: DetectorResult = state["detector_result"]

            session.add(
                TaskIteration(
                    task_id=task.id,
                    round_index=int(state["round_index"]),
                    prompt_group="rewrite",
                    prompt_name=state["prompt_name"],
                    prompt_version=state["prompt_version"],
                    rewritten_text=state["candidate_text"],
                    detector_score=detector_result.score,
                    detector_label=detector_result.label,
                    latency_ms=int(state["latency_ms"]),
                    detector_raw={
                        **detector_result.raw,
                        "llm_mode": llm_mode,
                    },
                )
            )
            await add_task_log(
                session,
                task_id=task.id,
                stage="round",
                level="info",
                message=f"第 {int(state['round_index'])} 轮完成。",
                detail={
                    "round": int(state["round_index"]),
                    "score": detector_result.score,
                    "label": detector_result.label,
                    "latency_ms": int(state["latency_ms"]),
                },
            )
            task.rounds_used = int(state["round_index"])
            await session.commit()

            updates: dict[str, Any] = {**state, "rounds_used": int(state["round_index"])}
            if not state["done"]:
                updates["round_index"] = int(state["next_round_index"])
                updates["current_text"] = state["next_text"]
            return updates

        def route_after_persist(state: dict[str, Any]) -> str:
            return END if bool(state["done"]) else "load_prompt"

        graph_builder = StateGraph(dict)
        graph_builder.add_node("load_prompt", load_prompt)
        graph_builder.add_node("rewrite_with_llm", rewrite_with_llm)
        graph_builder.add_node("detect_score", detect_score)
        graph_builder.add_node("decide_next", decide_next)
        graph_builder.add_node("persist_iteration", persist_iteration)

        graph_builder.add_edge(START, "load_prompt")
        graph_builder.add_edge("load_prompt", "rewrite_with_llm")
        graph_builder.add_edge("rewrite_with_llm", "detect_score")
        graph_builder.add_edge("detect_score", "decide_next")
        graph_builder.add_edge("decide_next", "persist_iteration")
        graph_builder.add_conditional_edges("persist_iteration", route_after_persist)

        graph = graph_builder.compile()

        initial_state: dict[str, Any] = {
            "task_id": task.id,
            "input_text": task.input_text,
            "current_text": task.input_text,
            "target_score": task.target_score,
            "max_rounds": task.max_rounds,
            "style": task.style,
            "round_index": 1,
            "best_score": 101.0,
            "best_text": "",
            "met_target": False,
            "done": False,
            "rounds_used": 0,
        }

        final_state = await graph.ainvoke(initial_state)

        task.best_text = str(final_state.get("best_text", "")) or task.input_text
        task.best_score = float(final_state.get("best_score", 100.0))
        task.met_target = bool(final_state.get("met_target", False))
        task.rounds_used = int(final_state.get("rounds_used", task.rounds_used))
        task.completed_at = datetime.now(timezone.utc)
        task.status = "success" if task.met_target else "not_met"
        await add_task_log(
            session,
            task_id=task.id,
            stage="agent",
            level="info" if task.met_target else "warning",
            message="任务执行结束。",
            detail={
                "status": task.status,
                "best_score": task.best_score,
                "rounds_used": task.rounds_used,
                "met_target": task.met_target,
            },
        )
        await session.commit()

    @staticmethod
    def _should_apply_external_rules(style: str) -> bool:
        style_name = style.strip().lower().replace("_", "-")
        return style_name == "deai-external"

    def _inject_external_rules(self, style_instruction: str) -> str:
        if self.external_rules_loader is None:
            return style_instruction
        suffix = self.external_rules_loader.build_instruction_suffix()
        if not suffix:
            return style_instruction
        if not style_instruction:
            return suffix
        return f"{style_instruction}\n\n{suffix}"
