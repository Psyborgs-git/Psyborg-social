# DSPy AI Pipelines

SocialMind uses DSPy to build, optimize, and compose all AI-driven behaviors. This document covers the DSPy philosophy, configuration, all pipeline definitions, and how to optimize them.

---

## Why DSPy

DSPy (Declarative Self-improving Python) separates **what** we want the LLM to do from **how** we prompt it. Instead of hand-writing prompts, we define:

1. **Signatures** — Input/output type contracts for each AI task
2. **Modules** — Composable units that use signatures
3. **Pipelines** — Multi-step chains of modules
4. **Optimizers** — Algorithms that tune prompts using labeled examples

When we switch LLMs (e.g., from Ollama/Llama to GPT-4o), DSPy re-optimizes prompts automatically. We don't maintain platform-specific prompt strings.

---

## LM Configuration

```python
# socialmind/ai/config.py
import dspy
import litellm
from socialmind.config.settings import settings

def configure_dspy():
    """Configure DSPy with the appropriate LM backend."""

    if settings.LLM_PROVIDER == "ollama":
        lm = dspy.LM(
            model=f"ollama_chat/{settings.OLLAMA_MODEL}",
            api_base=settings.OLLAMA_URL,  # http://ollama:11434
            max_tokens=2048,
            temperature=0.7,
        )
    elif settings.LLM_PROVIDER == "openai":
        lm = dspy.LM(
            model=f"openai/{settings.OPENAI_MODEL}",
            api_key=settings.OPENAI_API_KEY,
            max_tokens=2048,
        )
    elif settings.LLM_PROVIDER == "anthropic":
        lm = dspy.LM(
            model=f"anthropic/{settings.ANTHROPIC_MODEL}",
            api_key=settings.ANTHROPIC_API_KEY,
            max_tokens=2048,
        )
    elif settings.LLM_PROVIDER == "litellm":
        # Let LiteLLM route based on LITELLM_MODEL env var
        lm = dspy.LM(
            model=settings.LITELLM_MODEL,
            api_base=settings.LITELLM_BASE_URL,
            max_tokens=2048,
        )

    dspy.configure(lm=lm)
    return lm

# Embedding model (for research/retrieval)
def configure_embeddings():
    if settings.EMBED_PROVIDER == "ollama":
        return dspy.Embedder(
            model=f"ollama/{settings.OLLAMA_EMBED_MODEL}",
            api_base=settings.OLLAMA_URL,
        )
    return dspy.Embedder(model="openai/text-embedding-3-small")
```

---

## Signatures

Signatures define the typed contract for each AI task. DSPy uses these to generate, optimize, and validate prompts.

```python
# socialmind/ai/signatures/__init__.py
import dspy

class GeneratePost(dspy.Signature):
    """Generate an engaging social media post for the given platform and persona."""
    platform: str = dspy.InputField(desc="Target platform: instagram, tiktok, reddit, etc.")
    persona_description: str = dspy.InputField(desc="The author's voice, tone, niche, and style")
    topic_or_prompt: str = dspy.InputField(desc="Topic, prompt, or content direction")
    trending_context: str = dspy.InputField(desc="Current trending topics/hashtags in the niche", default="")
    post_text: str = dspy.OutputField(desc="The post text, ready to publish. Platform-appropriate length.")
    hashtags: list[str] = dspy.OutputField(desc="Relevant hashtags (empty list if platform doesn't use them)")
    image_prompt: str = dspy.OutputField(desc="DALL-E/SD prompt for accompanying image, or empty string if none needed")

class ReplyToDM(dspy.Signature):
    """Generate a natural, human-like reply to a direct message."""
    platform: str = dspy.InputField()
    persona_description: str = dspy.InputField()
    dm_text: str = dspy.InputField(desc="The incoming DM to reply to")
    conversation_history: str = dspy.InputField(desc="Previous messages in this thread", default="")
    sender_profile: str = dspy.InputField(desc="Brief info about the sender", default="")
    reply_text: str = dspy.OutputField(desc="Natural reply. Match the tone of the incoming message. Be concise.")

class GenerateComment(dspy.Signature):
    """Generate a relevant, engaging comment on a piece of content."""
    platform: str = dspy.InputField()
    persona_description: str = dspy.InputField()
    post_text: str = dspy.InputField(desc="The post being commented on")
    post_author: str = dspy.InputField(desc="Username of the post author")
    comment_intent: str = dspy.InputField(desc="agree, question, compliment, disagree, add_value", default="add_value")
    comment_text: str = dspy.OutputField(desc="The comment. Natural and on-topic. Under 200 chars for most platforms.")

class ResearchTrends(dspy.Signature):
    """Analyze scraped trending content and extract actionable insights."""
    platform: str = dspy.InputField()
    niche: str = dspy.InputField()
    raw_trending_items: str = dspy.InputField(desc="JSON list of trending posts/videos/threads")
    content_strategy: str = dspy.OutputField(desc="3-5 content ideas based on trends")
    top_hashtags: list[str] = dspy.OutputField(desc="Most relevant hashtags to use this week")
    trending_topics: list[str] = dspy.OutputField(desc="Key topics to reference in content")
    optimal_post_time: str = dspy.OutputField(desc="Best time to post based on engagement patterns")

class DecideShouldEngage(dspy.Signature):
    """Decide whether to engage with a piece of content (like/comment/share)."""
    persona_description: str = dspy.InputField()
    post_text: str = dspy.InputField()
    post_author: str = dspy.InputField()
    niche: str = dspy.InputField()
    should_like: bool = dspy.OutputField(desc="True if this post aligns with the persona's interests")
    should_comment: bool = dspy.OutputField(desc="True if a meaningful comment can be added")
    should_follow: bool = dspy.OutputField(desc="True if this author would be worth following")
    reason: str = dspy.OutputField(desc="Brief explanation for the decisions")

class GenerateStoryCaption(dspy.Signature):
    """Generate a caption/text overlay for a story post."""
    platform: str = dspy.InputField()
    persona_description: str = dspy.InputField()
    image_description: str = dspy.InputField(desc="What's in the image/video")
    story_text: str = dspy.OutputField(desc="Short text overlay for the story. Max 3 lines.")
    cta: str = dspy.OutputField(desc="Call-to-action (swipe up, reply, etc.), or empty string")

class AnalyzeSentiment(dspy.Signature):
    """Analyze the sentiment and intent of an incoming message."""
    message_text: str = dspy.InputField()
    sentiment: str = dspy.OutputField(desc="positive, negative, neutral, question, spam")
    intent: str = dspy.OutputField(desc="purchase_inquiry, complaint, compliment, question, spam, casual")
    urgency: str = dspy.OutputField(desc="high, medium, low")
    should_respond: bool = dspy.OutputField(desc="True if this message warrants a response")

class GenerateThreadOrTweetThread(dspy.Signature):
    """Generate a multi-part thread (Twitter/Threads)."""
    platform: str = dspy.InputField()
    persona_description: str = dspy.InputField()
    topic: str = dspy.InputField()
    thread_length: int = dspy.InputField(desc="Number of posts in the thread", default=5)
    posts: list[str] = dspy.OutputField(desc="List of post texts. Each under 280 chars for Twitter.")
```

---

## Modules

Modules wrap signatures with additional logic (chain-of-thought, retry, tool use).

```python
# socialmind/ai/modules/content.py
import dspy

class PostGenerator(dspy.Module):
    """Generates platform-appropriate posts with optional trend awareness."""

    def __init__(self):
        self.generate = dspy.TypedChainOfThought(GeneratePost)
        self.refine = dspy.TypedPredictor(RefineForPlatformLimits)

    def forward(self, platform: str, persona: Persona, topic: str, trends: list[TrendingItem]) -> PostContent:
        trending_context = "\n".join([f"- {t.title} ({', '.join(t.hashtags)})" for t in trends[:5]])

        result = self.generate(
            platform=platform,
            persona_description=persona.system_prompt,
            topic_or_prompt=topic,
            trending_context=trending_context,
        )

        # Enforce platform character limits
        result = self.refine(
            platform=platform,
            post_text=result.post_text,
            hashtags=result.hashtags,
        )

        return PostContent(
            text=result.post_text,
            hashtags=result.hashtags,
            image_prompt=result.image_prompt,
        )


class DMResponder(dspy.Module):
    """Analyzes incoming DMs and generates appropriate replies."""

    def __init__(self):
        self.analyze = dspy.TypedPredictor(AnalyzeSentiment)
        self.reply = dspy.TypedChainOfThought(ReplyToDM)

    def forward(
        self,
        dm: DirectMessage,
        persona: Persona,
        platform: str,
        history: list[DirectMessage],
    ) -> str | None:
        # First analyze the DM
        analysis = self.analyze(message_text=dm.text)

        # Don't respond to spam
        if analysis.intent == "spam" or not analysis.should_respond:
            return None

        history_text = "\n".join([f"{m.sender_username}: {m.text}" for m in history[-5:]])

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

    def __init__(self):
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

        comment_text = None
        if decision.should_comment:
            comment_result = self.comment(
                platform=feed_item.platform,
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

    def __init__(self):
        self.research = dspy.TypedChainOfThought(ResearchTrends)

    def forward(
        self,
        platform: str,
        niche: str,
        trending_items: list[TrendingItem],
    ) -> TrendReport:
        raw = json.dumps([{
            "title": t.title,
            "hashtags": t.hashtags,
            "score": t.engagement_score,
        } for t in trending_items])

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
```

---

## Pipelines

Pipelines compose multiple modules into full automation workflows.

```python
# socialmind/ai/pipelines/post_pipeline.py

class PostCampaignPipeline:
    """
    Full pipeline: research trends → generate content → generate image → publish.
    Used by Celery tasks for scheduled posts.
    """

    def __init__(self):
        self.researcher = TrendResearcher()
        self.generator = PostGenerator()
        self.dm_responder = DMResponder()

    async def run_post(
        self,
        account: Account,
        task: Task,
        adapter: BasePlatformAdapter,
    ) -> PostResult:
        # 1. Research current trends
        trending = await adapter.get_trending(
            niche=account.persona.niche,
            limit=20,
        )
        trend_report = self.researcher(
            platform=account.platform.slug,
            niche=account.persona.niche,
            trending_items=trending,
        )

        # 2. Generate post content
        topic = task.config.get("prompt") or trend_report.content_ideas[0]
        post_content = self.generator(
            platform=account.platform.slug,
            persona=account.persona,
            topic=topic,
            trends=trending,
        )

        # 3. Generate image if needed
        if post_content.image_prompt and task.config.get("include_image", True):
            media_url = await generate_image(post_content.image_prompt)
            post_content.media_urls = [media_url]

        # 4. Publish
        return await adapter.post(post_content)

    async def run_dm_responses(
        self,
        account: Account,
        adapter: BasePlatformAdapter,
    ) -> list[bool]:
        dms = await adapter.get_dms(unread_only=True)
        results = []
        for dm in dms:
            history = await adapter.get_dm_history(dm.thread_id, limit=10)
            reply = self.dm_responder(
                dm=dm,
                persona=account.persona,
                platform=account.platform.slug,
                history=history,
            )
            if reply:
                await asyncio.sleep(random.uniform(30, 120))  # Read delay
                result = await adapter.reply_dm(dm.dm_id, reply)
                results.append(result)
        return results
```

---

## Optimization

DSPy optimizers tune the prompts for each module automatically. Run optimization when you have labeled examples.

```python
# socialmind/ai/optimizers/optimize_post_generator.py
import dspy
from dspy.teleprompt import BootstrapFewShot, MIPROv2

def optimize_post_generator(training_examples: list[dspy.Example]):
    """
    Optimize the PostGenerator module using labeled examples.
    training_examples: list of Example(platform=..., persona_description=...,
                                       topic_or_prompt=..., post_text=...) with labels
    """
    module = PostGenerator()

    # Metric: engagement quality (simple heuristic; in production use real engagement data)
    def engagement_metric(example, prediction, trace=None):
        text = prediction.post_text
        has_hook = any(text.startswith(hook) for hook in ["Did you know", "The truth", "Stop"])
        has_cta = any(cta in text.lower() for cta in ["comment", "share", "follow", "tag"])
        length_ok = 100 < len(text) < 400
        return int(has_hook) + int(has_cta) + int(length_ok)

    optimizer = BootstrapFewShot(metric=engagement_metric, max_bootstrapped_demos=4)
    optimized = optimizer.compile(module, trainset=training_examples)

    # Save the optimized module
    optimized.save("socialmind/ai/optimized/post_generator.json")
    return optimized


def load_optimized_module(name: str) -> dspy.Module:
    """Load a previously optimized module from disk."""
    module_map = {
        "post_generator": PostGenerator,
        "dm_responder": DMResponder,
        "feed_engager": FeedEngager,
    }
    module = module_map[name]()
    module.load(f"socialmind/ai/optimized/{name}.json")
    return module
```

---

## Platform Character Limits

DSPy modules enforce these after generation:

| Platform | Post Limit | Comment Limit | DM Limit |
|---|---|---|---|
| Instagram | 2,200 chars | 2,200 chars | No hard limit |
| TikTok | 2,200 chars | 150 chars | No hard limit |
| Reddit | 40,000 chars | 10,000 chars | 10,000 chars |
| YouTube | 5,000 chars (desc) | 10,000 chars | — |
| Facebook | 63,206 chars | 8,000 chars | No hard limit |
| X (Twitter) | 280 chars | 280 chars | 10,000 chars |
| Threads | 500 chars | 500 chars | 1,000 chars |

---

## Persona System Prompt Template

Each persona's `system_prompt` feeds into every DSPy signature call:

```
You are {name}, a {niche} content creator on social media.

Voice & tone: {tone}
Writing style: {vocab_level} vocabulary, {emoji_usage} emoji usage
Language: {language}

Your personality:
- You share genuine insights about {niche}
- You engage authentically with your community
- You never sound robotic or corporate
- You use natural language, occasional slang, and real opinions

Hashtag style: {hashtag_strategy}

Do NOT:
- Use AI-sounding phrases like "I'd be happy to", "Certainly!", "As an AI"
- Write generic platitudes
- Repeat the same phrases across posts
- Sound promotional unless explicitly selling
```
