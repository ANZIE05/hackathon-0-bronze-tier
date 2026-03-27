"""LinkedIn AI content generator."""

import random
from datetime import datetime


def generate_linkedin_post(topic: str) -> str:
    """
    Generate a professional LinkedIn post about the given topic.

    Args:
        topic: The topic to generate content about (e.g., "AI agents for productivity")

    Returns:
        A formatted LinkedIn post with content and hashtags
    """
    hooks = [
        f"🚀 Let's talk about {topic}!",
        f"💡 Here's why {topic} matters in 2026:",
        f"🔥 Hot take: {topic} is changing the game.",
        f"📌 Quick thoughts on {topic}:",
        f"✨ {topic} - here's what you need to know:",
    ]

    insights = [
        f"The landscape of {topic} is evolving rapidly. Here are my key takeaways:",
        f"I've been exploring {topic} lately, and here's what I've learned:",
        f"Many professionals are asking about {topic}. Let me break it down:",
        f"After diving deep into {topic}, here are the insights worth sharing:",
    ]

    points = [
        "• Efficiency gains are real and measurable",
        "• Early adopters are seeing significant competitive advantages",
        "• The learning curve is worth the investment",
        "• Integration with existing workflows is smoother than expected",
        "• The community and resources available are growing exponentially",
    ]

    call_to_actions = [
        "What's your experience with this? Drop a comment below! 👇",
        "I'd love to hear your thoughts on this trend. 💬",
        "Are you leveraging this in your workflow? Let's discuss! 🤝",
        "Follow for more insights on productivity and tech! 📈",
    ]

    hashtags_list = [
        "#LinkedIn",
        "#ProfessionalDevelopment",
        "#CareerGrowth",
        "#Networking",
        "#Industry",
        "#Innovation",
        "#Technology",
        "#Productivity",
        "#AI",
        "#FutureOfWork",
        "#Leadership",
        "#Business",
    ]

    # Select random components
    hook = random.choice(hooks)
    insight = random.choice(insights)
    selected_points = random.sample(points, 3)
    cta = random.choice(call_to_actions)
    selected_hashtags = random.sample(hashtags_list, 5)

    # Build the post
    post = f"""{hook}

{insight}

{chr(10).join(selected_points)}

{cta}

{' '.join(selected_hashtags)}"""

    return post


if __name__ == "__main__":
    # Test the generator
    test_topic = "AI agents for productivity"
    print(generate_linkedin_post(test_topic))
