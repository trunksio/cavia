"""
LLM prompt templates for CV evaluation
"""

SYSTEM_PROMPT = """You are an expert HR professional evaluating CVs against specific criteria.

Your task is to:
1. Carefully analyze the CV data provided
2. Evaluate it against the given criterion
3. Provide a score from 0-100 where:
   - 0-20: Poor/Minimal fit
   - 21-40: Below average
   - 41-60: Average/Acceptable
   - 61-80: Good/Strong fit
   - 81-100: Excellent/Outstanding fit
4. Provide a confidence score from 0-1 indicating how certain you are
5. Extract evidence from the CV (direct quotes or specific data points)
6. Explain your reasoning clearly and objectively

Be objective, fair, and thorough. Consider both quantity and quality.
Base your evaluation solely on the information provided in the CV."""


def build_evaluation_prompt(parsed_cv: dict, criterion: dict) -> str:
    """
    Build evaluation prompt for LLM.

    Args:
        parsed_cv: ParsedCV as dict
        criterion: EvaluationCriterion as dict

    Returns:
        Formatted prompt string
    """
    # Format CV data for prompt
    contact_summary = _format_contact_info(parsed_cv.get("contact_info", {}))
    education_summary = _format_education(parsed_cv.get("education", []))
    experience_summary = _format_experience(parsed_cv.get("experience", []))
    skills_list = ", ".join(parsed_cv.get("skills", []))
    certs_summary = _format_certifications(parsed_cv.get("certifications", []))

    prompt = f"""
Evaluation Criterion:
━━━━━━━━━━━━━━━━━━
Name: {criterion['name']}
Description: {criterion['description']}
Evaluation Prompt: {criterion['evaluation_prompt']}
Weight: {criterion.get('weight', 1.0)}

━━━━━━━━━━━━━━━━━━

Candidate CV Data:
━━━━━━━━━━━━━━━━━━

{contact_summary}

EDUCATION:
{education_summary}

WORK EXPERIENCE:
{experience_summary}

SKILLS:
{skills_list}

CERTIFICATIONS:
{certs_summary}

━━━━━━━━━━━━━━━━━━

Provide your evaluation in the following JSON format (return ONLY the JSON, no other text):

{{
    "score": <integer from 0-100>,
    "confidence": <float from 0-1>,
    "evidence": "<direct quotes or specific data points from the CV that support your score>",
    "reasoning": "<your detailed explanation of why you assigned this score, referencing specific aspects of the CV>"
}}

Remember:
- Be specific and cite actual information from the CV
- Explain both strengths and weaknesses
- Be fair and objective
- Consider the criterion's weight in your evaluation
"""

    return prompt


def _format_contact_info(contact: dict) -> str:
    """Format contact info for prompt"""
    if not contact:
        return "Contact: Not provided"

    parts = []
    if contact.get("name"):
        parts.append(f"Name: {contact['name']}")
    if contact.get("email"):
        parts.append(f"Email: {contact['email']}")
    if contact.get("phone"):
        parts.append(f"Phone: {contact['phone']}")
    if contact.get("location"):
        parts.append(f"Location: {contact['location']}")
    if contact.get("linkedin"):
        parts.append(f"LinkedIn: {contact['linkedin']}")

    return "CONTACT INFO:\n" + "\n".join(parts)


def _format_education(education: list) -> str:
    """Format education entries for prompt"""
    if not education:
        return "No education information provided."

    entries = []
    for idx, edu in enumerate(education, 1):
        parts = [f"\n{idx}. {edu.get('degree', 'Degree not specified')}"]

        if edu.get("institution"):
            parts.append(f"   Institution: {edu['institution']}")
        if edu.get("start_date") or edu.get("end_date"):
            date_range = f"{edu.get('start_date', '?')} - {edu.get('end_date', 'Present')}"
            parts.append(f"   Dates: {date_range}")
        if edu.get("gpa"):
            parts.append(f"   GPA: {edu['gpa']}")

        entries.append("\n".join(parts))

    return "\n".join(entries)


def _format_experience(experience: list) -> str:
    """Format experience entries for prompt"""
    if not experience:
        return "No work experience provided."

    entries = []
    for idx, exp in enumerate(experience, 1):
        parts = [f"\n{idx}. {exp.get('title', 'Title not specified')}"]

        if exp.get("company"):
            parts.append(f"   Company: {exp['company']}")
        if exp.get("location"):
            parts.append(f"   Location: {exp['location']}")
        if exp.get("start_date") or exp.get("end_date"):
            date_range = f"{exp.get('start_date', '?')} - {exp.get('end_date', 'Present')}"
            parts.append(f"   Dates: {date_range}")
        if exp.get("description"):
            desc = exp['description'][:200]  # Truncate long descriptions
            parts.append(f"   Description: {desc}...")

        entries.append("\n".join(parts))

    return "\n".join(entries)


def _format_certifications(certifications: list) -> str:
    """Format certifications for prompt"""
    if not certifications:
        return "No certifications provided."

    entries = []
    for idx, cert in enumerate(certifications, 1):
        cert_str = f"{idx}. {cert.get('name', 'Certification not specified')}"
        if cert.get("issuer"):
            cert_str += f" (issued by {cert['issuer']})"
        if cert.get("date"):
            cert_str += f" - {cert['date']}"
        entries.append(cert_str)

    return "\n".join(entries)
