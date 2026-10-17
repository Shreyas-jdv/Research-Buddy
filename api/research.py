
import json
import os
from http.server import BaseHTTPRequestHandler

from openai import OpenAI


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        # Basic request-size limit.
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0

        if length <= 0 or length > 20000:
            return self.send_json(400, {"error": "Invalid request size."})

        try:
            body = json.loads(self.rfile.read(length))
            idea = str(body.get("idea", "")).strip()

            if not idea or len(idea) > 4000:
                return self.send_json(
                    400, {"error": "Provide an idea under 4000 characters."}
                )

            allowed = {
                "area": ["Agentic AI", "LLM Evaluation",
                         "AI Safety & Alignment", "Healthcare AI",
                         "Machine Learning", "Natural Language Processing"],
                "level": ["Weekend prototype", "Semester research project",
                          "Conference-style study"],
                "resources": ["One developer, laptop, API access",
                              "Small team and GPU access",
                              "Limited compute, open-source models",
                              "Research team and compute budget"],
                "priority": ["Strong experimental evidence",
                             "Novelty and publication potential",
                             "Build a working demo quickly",
                             "Social impact and practical value"]
            }

            settings = {}
            for field, choices in allowed.items():
                value = body.get(field, choices[0])
                if value not in choices:
                    return self.send_json(400, {
                        "error": f"Invalid value for {field}."
                    })
                settings[field] = value

            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                return self.send_json(
                    500, {"error": "Server API key is not configured."}
                )

            client = OpenAI(api_key=api_key)

            schema = {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "hypothesis": {"type": "string"},
                    "rationale": {"type": "string"},
                    "novelty": {"type": "string"},
                    "gap": {"type": "string"},
                    "falsification": {"type": "string"},
                    "experiments": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "metrics": {
                        "type": "array",
                        "items": {
                            "type": "array",
                            "items": {"type": "string"}
                        }
                    },
                    "risks": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "protocol": {
                        "type": "array",
                        "items": {"type": "string"}
                    },
                    "next": {
                        "type": "array",
                        "items": {"type": "string"}
                    }
                },
                "required": [
                    "question", "hypothesis", "rationale", "novelty",
                    "gap", "falsification", "experiments", "metrics",
                    "risks", "protocol", "next"
                ],
                "additionalProperties": False
            }

            instructions = """
You are Research Co-Founder, a rigorous AI research collaborator.

Produce a feasible, critical research plan for the user's idea.
Do not simply agree with the premise. Identify what would disprove
the hypothesis and separate established facts from assumptions.

Return:
- One precise research question and falsifiable hypothesis.
- Rationale, likely research gap and a novelty-check recommendation.
- Four controlled experiments including baselines or ablations.
- Five measurable evaluation metrics with concise definitions.
- A falsification criterion, realistic risks and reproducibility steps.
- Four actionable next steps.

Adapt the plan to the supplied research area, project scope,
resources and priority. Do not fabricate papers, citations, results,
or claims of novelty. No experiments or literature searches have
been performed unless explicitly supplied as evidence.
Keep the plan concrete enough for a student developer to execute.
"""

            response = client.responses.create(
                model="gpt-4.1-mini",
                instructions=instructions,
                input=json.dumps({
                    "idea": idea,
                    **settings
                }),
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "research_plan",
                        "strict": True,
                        "schema": schema
                    }
                }
            )

            result = json.loads(response.output_text)
            return self.send_json(200, result)

        except json.JSONDecodeError:
            return self.send_json(400, {"error": "Invalid JSON request."})
        except Exception:
            # Do not expose API keys or internal stack traces.
            return self.send_json(
                502, {"error": "Research generation failed. Check API access and server logs."}
            )

    def do_OPTIONS(self):
        return self.send_json(405, {"error": "Method not allowed."})

    def send_json(self, status, data):
        payload = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(payload)
