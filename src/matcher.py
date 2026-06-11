"""
Resume-based job relevance scoring for Shreyas Reddy Gaddampally.

Weighted scoring:
  HIGH (2 pts) — skills actively used in experience/projects
  LOW  (1 pt)  — skills listed in skills section only
"""

# Used directly in internship, research, or projects → worth more
HIGH_WEIGHT_KEYWORDS = {
    # Languages used in experience
    "python", "golang", "go", "typescript",
    # Cloud used at EchoStar / research
    "aws", "gcp", "s3", "ec2", "lambda", "bedrock", "watsonx",
    # Databases used in experience
    "postgresql", "postgres", "redis", "sqlite",
    # Frameworks used in experience
    "fastapi", "grpc", "rest", "restful",
    # Infrastructure used at EchoStar
    "docker", "microservices",
    # Distributed systems (multiple projects)
    "distributed", "backend", "api",
    # AI/ML used in experience + visiting scholar
    "rag", "llm", "genai", "generative ai", "langchain",
    "embedding", "vector", "retrieval", "openai",
    # Reliability (EchoStar internship work)
    "latency", "throughput", "scalable",
}

# Listed in skills section but not prominently used in experience → worth less
LOW_WEIGHT_KEYWORDS = {
    # Languages
    "java", "javascript", "sql", "c++",
    # Cloud / infra
    "azure", "gcp", "cloud", "kubernetes", "terraform", "serverless",
    # Databases
    "mysql", "mongodb", "dynamodb", "oracle",
    # Frameworks
    "spring boot", "spring", "node.js", "nodejs", "flask", "kafka", "rabbitmq",
    # AI/ML
    "pytorch", "machine learning", "nlp", "ai",
    # Practices
    "ci/cd", "devops", "agile", "git", "code review",
    # Reliability
    "sre", "site reliability", "observability", "monitoring", "prometheus",
    # General
    "systems design", "high availability", "concurrency",
}

# Jobs with these in the title are out of scope — skipped without fetching description
EXCLUDE_TITLE_KEYWORDS = {
    # Mobile / non-web platforms
    "ios", "android", "mobile", "swift", "kotlin", "flutter", "react native",
    # Hardware / embedded
    "embedded", "firmware", "hardware", "fpga", "verilog", "vlsi", "asic",
    # Ecosystems we don't use
    ".net", "c#", "unity", "salesforce", "sap",
    # Wrong role type
    "data analyst",
    "qa engineer", "test engineer", "quality assurance",
    "network engineer", "network administrator",
    "it support", "help desk", "desktop support",
    "security analyst", "penetration tester",
    # Pure Java roles
    "java developer", "java engineer",
    # Seniority — out of range for current profile
    "senior", "sr.", "staff", "principal", "lead engineer",
    "engineering manager", "director", "vp of", "head of engineering",
}

CITIZENSHIP_PHRASES = {
    "us citizen",
    "u.s. citizen",
    "united states citizen",
    "must be a citizen",
    "citizenship required",
    "citizenship is required",
    "requires citizenship",
    "active secret clearance",
    "active top secret",
    "security clearance required",
    "clearance required",
    "secret clearance",
    "top secret clearance",
    "ts/sci",
    "ts sci",
    "dod clearance",
    "government clearance",
}


def is_excluded_by_title(title: str) -> bool:
    t = title.lower()
    # Exclude if title contains "java" as a standalone word (not "javascript")
    if "java" in t and "javascript" not in t:
        return True
    return any(kw in t for kw in EXCLUDE_TITLE_KEYWORDS)


def requires_citizenship(description: str) -> bool:
    text = description.lower()
    return any(phrase in text for phrase in CITIZENSHIP_PHRASES)


def score_job(title: str, description: str) -> tuple:
    """
    Weighted resume scoring.
    Returns (score: int, matched_skills: str).

    High-weight keywords (from experience/projects) = 2 pts each.
    Low-weight keywords (skills section only)        = 1 pt each.
    """
    text = (title + " " + description).lower()

    high_matched = sorted(kw for kw in HIGH_WEIGHT_KEYWORDS if kw in text)
    low_matched  = sorted(kw for kw in LOW_WEIGHT_KEYWORDS  if kw in text)

    score = len(high_matched) * 2 + len(low_matched) * 1

    all_matched = [f"{kw}(2)" for kw in high_matched] + [f"{kw}(1)" for kw in low_matched]
    return score, ", ".join(all_matched)
