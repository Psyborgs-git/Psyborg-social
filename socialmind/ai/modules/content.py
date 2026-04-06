from __future__ import annotations

import json
from dataclasses import dataclass
from typing import TYPE_CHECKING

import dspy

from socialmind.adapters.base import DirectMessage, FeedItem, PostContent, TrendingItem
from socialmind.ai.signatures import (
    AnalyzeSentiment,
    DecideShouldEngage,
    GenerateComment,
    GeneratePost,
    RefineForPlatformLimits,
    ReplyToDM,
    ResearchTrends,
)

if TYPE_CHECKING:
    from socialmind.models.persona import Persona


@dataclass
class EngagementPlan:
    should_like: bool
    should_comment: bool
    should_follow: bool
    comment_text: str | None = None


@dataclass
class TrendReport:
    content_ideas: list[str]
    top_hashtags: list[str]
    trending_topics: list[str]
    optimal_post_time: str


class PostGenerator(dspy.Module):
    """Generates platform-appropriate posts with optional trend awareness."""

    def __init__(self) -> None:
        self.generate = dspy.TypedChainOfThought(GeneratePost)
        self.refine = dspy.TypedPredictor(RefineForPlatformLimits)

    def forward(
        self,
        platform: str,
        persona: Persona,
        topic: str,
        trends: list[TrendingItem],
    ) -> PostContent:
        trending_context = "\n".join(
            [f"- {t.title} ({', '.join(t.hashtags)})" for t in trends[:5]]
        )

        result = self.generate(
            platform=platform,
            persona_description=persona.system_prompt,
            topic_or_prompt=topic,
            trending_context=trending_context,
        )

        refined = self.refine(
            platform=platform,
            draft_post_text=result.post_text,
            draft_hashtags=result.hashtags,
        )

        return PostContent(
            text=refined.post_text,
            hashtags=refined.hashtags,
            metadata={"image_prompt": result.image_prompt},
        )


class DMResponder(dspy.Module):
    """Analyzes incoming DMs and generates appropriate replies."""

    def __init__(self) -> None:
        self.analyze = dspy.TypedPredictor(AnalyzeSentiment)
        self.reply = dspy.TypedChainOfThought(ReplyToDM)

    def forward(
        self,
        dm: DirectMessage,
        persona: Persona,
        platform: str,
        history: list[DirectMessage],
    ) -> str | None:
        analysis = self.analyze(message_text=dm.text)

        if analysis.intent == "spam" or not analysis.should_respond:
            return None

        history_text = "\n".join(
            [f"{m.sender_username}: {m.text}" for m in history[-5:]]
        )

        result = self.reply(
            platform=platform,
            persona_description=persona.system_prompt,
            dm_text=dm.text,
            conversation_history=history_text,
            sender_profile=f"@{dm.sender_username}",
        )

        return result.reply_text


class FeedEngager(dspy.Module):
    """Reviews feed items and decides engagement actions."""

    def __init__(self) -> None:
        self.decide = dspy.TypedPredictor(DecideShouldEngage)
        self.comment = dspy.TypedChainOfThought(GenerateComment)

    def forward(
        self,
        feed_item: FeedItem,
        persona: Persona,
        niche: str,
    ) -> EngagementPlan:
        decision = self.decide(
            persona_description=persona.system_prompt,
            post_text=feed_item.text,
            post_author=feed_item.author_username,
            niche=niche,
        )

        comment_text: str | None = None
        if decision.should_comment:
            comment_result = self.comment(
                platform="",
                persona_description=persona.system_prompt,
                post_text=feed_item.text,
                post_author=feed_item.author_username,
            )
            comment_text = comment_result.comment_text

        return EngagementPlan(
            should_like=decision.should_like,
            should_comment=decision.should_comment,
            should_follow=decision.should_follow,
            comment_text=comment_text,
        )


class TrendResearcher(dspy.Module):
    """Analyzes trending content and produces a content strategy."""

    def __init__(self) -> None:
        self.research = dspy.TypedChainOfThought(ResearchTrends)

    def forward(
        self,
        platform: str,
        niche: str,
        trending_items: list[TrendingItem],
    ) -> TrendReport:
        raw = json.dumps(
            [
                {
                    "title": t.title,
                    "hashtags": t.hashtags,
                    "score": t.engagement_score,
                }
                for t in trending_items
            ]
        )

        result = self.research(
            platform=platform,
            niche=niche,
            raw_trending_items=raw,
        )

        return TrendReport(
            content_ideas=result.content_strategy.split("\n"),
            top_hashtags=result.top_hashtags,
            trending_topics=result.trending_topics,
            optimal_post_time=result.optimal_post_time,
        )


__all__ = [
    "EngagementPlan",
    "TrendReport",
    "PostGenerator",
    "DMResponder",
    "FeedEngager",
    "TrendResearcher",
]
