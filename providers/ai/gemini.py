import os

import vertexai
from vertexai.generative_models import GenerativeModel


class GeminiProvider:
    def __init__(self):
        project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
        location = os.getenv("GOOGLE_CLOUD_LOCATION", "europe-west1")
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        if not project_id:
            raise ValueError(
                "GOOGLE_CLOUD_PROJECT must be set when AI_PROVIDER=gemini"
            )

        vertexai.init(
            project=project_id,
            location=location,
        )

        self.model = GenerativeModel(model_name)

    def analyze(self, finding):
        prompt = (
            "You are a cloud security assistant. "
            "Explain this security finding in simple language, "
            "include the risk, and give one short recommended action.\n\n"
            f"Finding: {finding}"
        )

        response = self.model.generate_content(prompt)

        return response.text
