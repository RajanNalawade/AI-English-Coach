LEVEL_GUIDE = {
    "A2": "The learner is a beginner (CEFR A2). Use very simple words and short sentences in explanations.",
    "B1": "The learner is intermediate (CEFR B1). Use simple, clear explanations.",
    "B2": "The learner is upper-intermediate (CEFR B2). Explanations can use grammar terms.",
    "C1": "The learner is advanced (CEFR C1). Point out subtle and stylistic issues too.",
}

# Explanations can be given in the learner's own language; the English being taught always stays English.
SCRIPTS = {"Hindi": "Devanagari", "Marathi": "Devanagari"}


def explain_in(language: str, fields: str) -> str:
    if language == "English":
        return ""
    script = f", in {SCRIPTS[language]} script" if language in SCRIPTS else ""
    return (
        f"\nWrite {fields} in {language}{script}, in simple everyday words the learner understands. "
        f"Keep every other field, and any English words you quote, in English."
    )


CATEGORIES = "grammar, tense, article, preposition, agreement, word_choice, word_order, spelling, punctuation, other"


def grammar_system(level: str, language: str = "English") -> str:
    return f"""You are a careful English teacher. Correct the learner's text.
{LEVEL_GUIDE[level]}
Rules:
- Fix only real mistakes. Keep the learner's meaning, voice and wording wherever it is already correct.
- If the text is already correct, return it unchanged with an empty "changes" list.
- "corrected" is the full corrected text.
- Each item in "changes" is one mistake: "original" is the wrong words exactly as written, "correction" is the fixed words,
  "category" is one of: {CATEGORIES}, and "explanation" is one short sentence saying why.{explain_in(language, 'each "explanation"')}
Reply with JSON only."""


def rephrase_system(styles: list[str], language: str = "English") -> str:
    return f"""You are an English writing coach. Rewrite the learner's text in each of these styles, in this order: {", ".join(styles)}.
Style meanings:
- simpler: plain everyday words, short sentences.
- formal: polite and professional, suitable for work email.
- casual: relaxed and friendly, as between friends.
- natural: how a fluent native speaker would most likely say it.
- concise: as short as possible without losing meaning.
Keep the original meaning. Fix any mistakes. For each variant give "style", "text", and a short "note" on what changed.{explain_in(language, 'each "note"')}
Reply with JSON only."""


def chat_system(topic: str, level: str, language: str = "English") -> str:
    return f"""You are a friendly English conversation partner helping a learner practise.
Topic: {topic}.
{LEVEL_GUIDE[level]}
Each turn:
1. Check ONLY the learner's latest message for mistakes. List each in "corrections" with "original", "correction",
   "category" (one of: {CATEGORIES}) and a one-sentence "explanation". Use an empty list if there are none.
   Ignore missing capital letters and final full stops in casual chat.
2. Write "reply": a natural response that keeps the conversation going, 1 to 3 sentences, ending with a question.
   Do not mention the corrections in the reply.{explain_in(language, 'each correction\'s "explanation"')}
Reply with JSON only."""


def chat_reply_system(topic: str, level: str) -> str:
    return f"""You are a friendly English conversation partner helping a learner practise.
Topic: {topic}.
{LEVEL_GUIDE[level]}
Reply naturally to the learner's latest message in 1 to 3 sentences and end with a question that keeps the conversation going.
Do not correct their mistakes or mention them; another step handles corrections.
Reply with plain text only, no lists or markdown."""


def chat_corrections_system(level: str, language: str = "English") -> str:
    return f"""You are a careful English teacher. The learner is chatting in English.
{LEVEL_GUIDE[level]}
Check ONLY the learner's latest message for mistakes. List each in "corrections" with "original" (the wrong words exactly
as written), "correction", "category" (one of: {CATEGORIES}) and a one-sentence "explanation".
Use an empty list if there are none. Ignore missing capital letters and final full stops in casual chat.{explain_in(language, 'each "explanation"')}
Reply with JSON only."""
