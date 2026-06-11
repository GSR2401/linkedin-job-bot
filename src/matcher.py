"""
Resume-based job relevance scoring for Shreyas Reddy Gaddampally.
Skills: Python, Go, Java, TypeScript, AWS, GCP, Docker, Kubernetes,
        PostgreSQL, Redis, FastAPI, gRPC, RAG, LLMs, Distributed Systems.
"""

RESUME_KEYWORDS = {
    # Languages
    "python", "golang", "go", "java", "typescript", "javascript", "sql", "c++",
    # Cloud & Infrastructure
    "aws", "gcp", "azure", "cloud", "s3", "ec2", "lambda", "bedrock",
    "kubernetes", "docker", "terraform", "serverless",
    # Databases
    "postgresql", "postgres", "mysql", "redis", "mongodb", "dynamodb", "sqlite",
    # Frameworks & APIs
    "fastapi", "spring boot", "spring", "node.js", "nodejs", "flask",
    "rest", "restful", "grpc", "kafka", "rabbitmq",
    # Distributed & Backend
    "distributed", "microservices", "backend", "api", "systems design",
    "high availability", "scalable", "concurrency",
    # AI / ML
    "ai", "llm", "rag", "genai", "generative ai", "langchain", "pytorch",
    "machine learning", "nlp", "embedding", "vector", "retrieval",
    "openai", "bedrock", "watsonx",
    # Practices
    "ci/cd", "devops", "agile", "git", "code review",
    # Reliability
    "sre", "site reliability", "observability", "monitoring", "prometheus",
    "latency", "throughput",
}

# Jobs with these in the title are clearly out of scope — skip without fetching description
EXCLUDE_TITLE_KEYWORDS = {
    "ios", "android", "mobile", "swift", "kotlin", "flutter", "react native",
    "embedded", "firmware", "hardware", "fpga", "verilog", "vlsi", "asic",
    ".net", "c#", "unity",
    "salesforce", "sap",
    "data analyst",
    "qa engineer", "test engineer", "quality assurance",
    "network engineer", "network administrator",
    "it support", "help desk", "desktop support",
    "security analyst", "penetration tester",
    "front end only", "ui engineer",
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
    "must hold.*clearance",
}


def is_excluded_by_title(title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in EXCLUDE_TITLE_KEYWORDS)


def requires_citizenship(description: str) -> bool:
    """Return True if the job description requires US citizenship or security clearance."""
    text = description.lower()
    return any(phrase in text for phrase in CITIZENSHIP_PHRASES)


def score_job(title: str, description: str) -> tuple:
    """
    Score a job against resume keywords.
    Returns (score: int, matched_skills: str).
    Score = number of distinct resume keywords found in title + description.
    """
    text = (title + " " + description).lower()
    matched = sorted(kw for kw in RESUME_KEYWORDS if kw in text)
    return len(matched), ", ".join(matched)
