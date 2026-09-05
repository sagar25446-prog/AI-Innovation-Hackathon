"""Pydantic models mirroring ``packages/contracts/lesson-contract.schema.json``.

The JSON schema stays the single source of truth; these models are its Python
projection. ``extra="allow"`` on the contract responses keeps the additive
fields (``groundingStatus``, ``tier``, ``estimatedSeconds``) legal without
forking the schema.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Level = Literal["beginner", "intermediate", "advanced"]
Language = Literal[
    # Core teaching languages (hand-authored narration).
    "english", "hindi", "hinglish",
    # Extended languages (localised on demand by services.translation).
    "bengali", "gujarati", "kannada", "malayalam", "marathi",
    "nepali", "odia", "punjabi", "sinhala", "tamil", "telugu", "urdu",
]
Personality = Literal["patient", "socratic", "coach"]
StudyMode = Literal["lesson", "exam", "revision"]
VisualType = Literal[
    "circuit", "equation", "graph", "timeline", "diagram", "code_trace", "concept_map"
]
NextAction = Literal["advance", "repair", "retry"]


class LearnerProfile(BaseModel):
    level: Level
    language: Language
    availableMinutes: int = Field(ge=1, le=10080)
    goal: str = Field(min_length=1)
    priorKnowledge: str | None = None
    personality: Personality | None = None


class SourceCitation(BaseModel):
    documentId: str
    pageOrSlide: int = Field(ge=1)
    heading: str | None = None
    excerpt: str


class VisualSpec(BaseModel):
    type: VisualType
    data: dict[str, Any]


class Scene(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    conceptId: str
    objective: str
    narration: str
    visual: VisualSpec
    citations: list[SourceCitation]
    durationSeconds: int = Field(ge=1)
    checkpointId: str | None = None


class LessonPlan(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    learner: LearnerProfile
    scenes: list[Scene] = Field(min_length=1)


class EvaluationResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    correct: bool
    mastery: float = Field(ge=0, le=1)
    misconception: str | None = None
    feedback: str
    nextAction: NextAction
    repairScene: Scene | None = None


# ---------------------------------------------------------------------------
# Request bodies
# ---------------------------------------------------------------------------


class MaterialRequest(BaseModel):
    """Either a topic to look up, or raw text to ingest."""

    topic: str | None = None
    text: str | None = None
    title: str | None = None


class PlanRequest(BaseModel):
    learner: LearnerProfile
    materialId: str | None = None
    topic: str = "Ohm's Law"
    studentId: str = "student-demo"
    studyMode: StudyMode = "lesson"


class AnswerRequest(BaseModel):
    answer: str = ""
    optionId: str | None = None
    language: Language | None = None
    studentId: str = "student-demo"


class QuizResponse(BaseModel):
    questionId: str
    # Free text for short answers, an option id for MCQs, a number (as text)
    # for numeric problems. The grader knows which by question type.
    response: str = ""


class QuizSubmission(BaseModel):
    responses: list[QuizResponse] = []


class MisconceptionRecord(BaseModel):
    id: str
    status: str
    concept: str


class NextTopic(BaseModel):
    id: str
    title: str


class LearningReport(BaseModel):
    studentId: str
    lessonId: str
    score: float
    strongConcepts: list[str]
    weakConcepts: list[str]
    misconceptions: list[MisconceptionRecord]
    revisionActions: list[str]
    nextTopic: NextTopic
    totalTimeSeconds: int
    scenesCompleted: int
    checkpointsPassed: int
    checkpointsFailed: int
    # Present once the learner has taken the end-of-lesson quiz. None means the
    # score above is inferred from checkpoint evidence instead.
    quizTaken: bool = False
    quizScore: float | None = None
    quizVerdict: str | None = None
    quizCorrect: int | None = None
    quizTotal: int | None = None
