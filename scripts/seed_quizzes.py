import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import db

SAMPLE_QUIZZES = [
    {
        "question": "حرف 'ب' qanday talaffuz qilinadi?",
        "options": ["Ba", "Ta", "Sa", "Ja"],
        "correct_option_index": 0,
        "level": "beginner",
    },
    {
        "question": "'كتاب' so'zi nimani anglatadi?",
        "options": ["Qalam", "Kitob", "Stol", "Deraza"],
        "correct_option_index": 1,
        "level": "beginner",
    },
    {
        "question": "Tanwin nima uchun ishlatiladi?",
        "options": [
            "Nominativ holat belgisi",
            "So'z oxiridagi noaniqlik (n) tovushi",
            "Fe'l zamoni",
            "Ko'plik shakli",
        ],
        "correct_option_index": 1,
        "level": "intermediate",
    },
]


def seed() -> None:
    for quiz in SAMPLE_QUIZZES:
        db.collection("quizzes").document().set(quiz)
    print(f"Seeded {len(SAMPLE_QUIZZES)} quiz questions.")


if __name__ == "__main__":
    seed()
