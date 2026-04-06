from __future__ import annotations

import dspy


class GeneratePost(dspy.Signature):
    """Generate an engaging social media post for the given platform and persona."""

    platform: str = dspy.InputField(desc="Target platform: instagram, tiktok, reddit, etc.")
    persona_description: str = dspy.InputField(desc="The author's voice, tone, niche, and style")
    topic_or_prompt: str = dspy.InputField(desc="Topic, prompt, or content direction")
    trending_context: str = dspy.InputField(
        desc="Current trending topics/hashtags in the niche", default=""
    )
    post_text: str = dspy.OutputField(
        desc="The post text, ready to publish. Platform-appropriate length."
    )
    hashtags: list[str] = dspy.OutputField(
        desc="Relevant hashtags (empty list if platform doesn't use them)"
    )
    image_prompt: str = dspy.OutputField(
        desc="DALL-E/SD prompt for accompanying image, or empty string if none needed"
    )


class ReplyToDM(dspy.Signature):
    """Generate a natural, human-like reply to a direct message."""

    platform: str = dspy.InputField()
    persona_description: str = dspy.InputField()
    dm_text: str = dspy.InputField(desc="The incoming DM to reply to")
    conversation_history: str = dspy.InputField(
        desc="Previous messages in this thread", default=""
    )
    sender_profile: str = dspy.InputField(desc="Brief info about the sender", default="")
    reply_text: str = dspy.OutputField(
        desc="Natural reply. Match the tone of the incoming message. Be concise."
    )


class GenerateComment(dspy.Signature):
    """Generate a relevant, engaging comment on a piece of content."""

    platform: str = dspy.InputField()
    persona_description: str = dspy.InputField()
    post_text: str = dspy.InputField(desc="The post being commented on")
    post_author: str = dspy.InputField(desc="Username of the post author")
    comment_intent: str = dspy.InputField(
        desc="agree, question, compliment, disagree, add_value", default="add_value"
    )
    comment_text: str = dspy.OutputField(
        desc="The comment. Natural and on-topic. Under 200 chars for most platforms."
    )


class ResearchTrends(dspy.Signature):
    """Analyze scraped trending content and extract actionable insights."""

    platform: str = dspy.InputField()
    niche: str = dspy.InputField()
    raw_trending_items: str = dspy.InputField(desc="JSON list of trending posts/videos/threads")
    content_strategy: str = dspy.OutputField(desc="3-5 content ideas based on trends")
    top_hashtags: list[str] = dspy.OutputField(desc="Most relevant hashtags to use this week")
    trending_topics: list[str] = dspy.OutputField(desc="Key topics to reference in content")
    optimal_post_time: str = dspy.OutputField(
        desc="Best time to post based on engagement patterns"
    )


class DecideShouldEngage(dspy.Signature):
    """Decide whether to engage with a piece of content (like/comment/share)."""

    persona_description: str = dspy.InputField()
    post_text: str = dspy.InputField()
    post_author: str = dspy.InputField()
    niche: str = dspy.InputField()
    should_like: bool = dspy.OutputField(
        desc="True if this post aligns with the persona's interests"
    )
    should_comment: bool = dspy.OutputField(
        desc="True if a meaningful comment can be added"
    )
    should_follow: bool = dspy.OutputField(
        desc="True if this author would be worth following"
    )
    reason: str = dspy.OutputField(desc="Brief explanation for the decisions")


class GenerateStoryCaption(dspy.Signature):
    """Generate a caption/text overlay for a story post."""

    platform: str = dspy.InputField()
    persona_description: str = dspy.InputField()
    image_description: str = dspy.InputField(desc="What's in the image/video")
    story_text: str = dspy.OutputField(
        desc="Short text overlay for the story. Max 3 lines."
    )
    cta: str = dspy.OutputField(
        desc="Call-to-action (swipe up, reply, etc.), or empty string"
    )


class AnalyzeSentiment(dspy.Signature):
    """Analyze the sentiment and intent of an incoming message."""

    message_text: str = dspy.InputField()
    sentiment: str = dspy.OutputField(
        desc="positive, negative, neutral, question, spam"
    )
    intent: str = dspy.OutputField(
        desc="purchase_inquiry, complaint, compliment, question, spam, casual"
    )
    urgency: str = dspy.OutputField(desc="high, medium, low")
    should_respond: bool = dspy.OutputField(
        desc="True if this message warrants a response"
    )


class GenerateThreadOrTweetThread(dspy.Signature):
    """Generate a multi-part thread (Twitter/Threads)."""

    platform: str = dspy.InputField()
    persona_description: str = dspy.InputField()
    topic: str = dspy.InputField()
    thread_length: int = dspy.InputField(
        desc="Number of posts in the thread", default=5
    )
    posts: list[str] = dspy.OutputField(
        desc="List of post texts. Each under 280 chars for Twitter."
    )


class RefineForPlatformLimits(dspy.Signature):
    """Refine a post to fit platform character limits."""

    platform: str = dspy.InputField(desc="Target platform")
    draft_post_text: str = dspy.InputField(desc="Draft post text")
    draft_hashtags: list[str] = dspy.InputField(desc="Draft hashtags")
    post_text: str = dspy.OutputField(desc="Refined post text within platform limits")
    hashtags: list[str] = dspy.OutputField(desc="Refined hashtag list")


__all__ = [
    "GeneratePost",
    "ReplyToDM",
    "GenerateComment",
    "ResearchTrends",
    "DecideShouldEngage",
    "GenerateStoryCaption",
    "AnalyzeSentiment",
    "GenerateThreadOrTweetThread",
    "RefineForPlatformLimits",
]
