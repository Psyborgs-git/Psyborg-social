from __future__ import annotations

import dspy
from dspy.teleprompt import BootstrapFewShot

from socialmind.ai.modules.content import DMResponder, FeedEngager, PostGenerator


def optimize_post_generator(
    training_examples: list[dspy.Example],
) -> dspy.Module:
    """
    Optimize the PostGenerator module using labeled examples.

    training_examples: list of Example(platform=..., persona_description=...,
                                       topic_or_prompt=..., post_text=...) with labels
    """
    module = PostGenerator()

    def engagement_metric(
        example: dspy.Example,
        prediction: dspy.Prediction,
        trace: object = None,
    ) -> int:
        text = getattr(prediction, "post_text", "") or ""
        has_hook = any(
            text.startswith(hook)
            for hook in ["Did you know", "The truth", "Stop", "Why", "What"]
        )
        has_cta = any(
            cta in text.lower()
            for cta in ["comment", "share", "follow", "tag", "save", "like"]
        )
        length_ok = 100 < len(text) < 400
        return int(has_hook) + int(has_cta) + int(length_ok)

    optimizer = BootstrapFewShot(metric=engagement_metric, max_bootstrapped_demos=4)
    optimized = optimizer.compile(module, trainset=training_examples)

    import os

    os.makedirs("socialmind/ai/optimized", exist_ok=True)
    optimized.save("socialmind/ai/optimized/post_generator.json")
    return optimized


def load_optimized_module(name: str) -> dspy.Module:
    """Load a previously optimized module from disk."""
    module_map: dict[str, type[dspy.Module]] = {
        "post_generator": PostGenerator,
        "dm_responder": DMResponder,
        "feed_engager": FeedEngager,
    }
    module = module_map[name]()
    module.load(f"socialmind/ai/optimized/{name}.json")
    return module
