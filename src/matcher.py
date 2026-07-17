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

# Staffing / recruiting / IT-consulting firms — post roles on behalf of other
# companies rather than hiring directly. Matched against the normalized company name.
EXCLUDED_COMPANIES = {
    # Major repeated names
    "aditi consulting", "akraya", "aquent", "beaconfire", "brooksource",
    "collabera", "conexess group", "consultnet technology services and solutions",
    "cybercoders", "dewinter group", "eclaro", "emonics", "global technical talent",
    "green key resources", "huxley", "inceed", "insight global", "intellipro",
    "jobot", "kforce", "lancesoft", "marketeq talent", "mitchell martin",
    "motion recruitment", "primary talent partners", "ptr global", "robert half",
    "shrinq consulting group", "talentburst", "the fountain group",
    "v-soft consulting group", "winaxis",

    # Additional recruiting, staffing, or consulting firms
    "a-line staffing solutions", "ace recovery group", "acumenz consulting",
    "agelix consulting", "alexander chapman", "applications international",
    "avenue code", "bayforce", "bayro", "bridgeflair", "btg", "cai", "captech",
    "ccs it", "celebal technologies", "codex tech-it", "cogent communications",
    "concorde research technologies", "cps", "cube hub",
    "develow fsd", "diyar united company", "dream catchers recruitment agency",
    "eleven recruiting", "eliassen group", "elevanta partners", "espo",
    "evona", "fintal partners", "flagler technologies", "fortray global service",
    "gyga force", "hyr global source", "iconsultera", "innovatech staffing",
    "innovee consulting", "intepros", "james search group", "k9 recruitment",
    "kellymitchell group", "khyathi informatics", "kmm technologies",
    "kotra global talent center", "lucas james talent partners", "matlen silver",
    "matricstek", "millennium software and staffing", "navitas business consulting",
    "ntech workforce", "odyssey information services", "okaya infocom",
    "orion innovation", "piper maddox", "planet pharma", "prolim",
    "prosum", "proven recruiting", "q1 technologies", "rsc solutions", "saragossa",
    "sgs consulting", "sharp decisions", "shields group search", "sotalent",
    "stefanini north america", "stefanini", "stellar consulting solutions",
    "synthires", "synechron", "tte staffing", "ultratalent", "unipro international",
    "ursus", "valorem reply", "ventures unlimited",
    "webologix", "xstear incorporation", "zealtech",

    # Job platforms, aggregators, and talent networks
    "turing", "jobgether", "why hiring", "remotehunter", "dream jobs in sports",
    "web3 openjobs", "careerscape", "shortlist", "workgenius group",

    # Training, career-support, or placement programs
    "per scholas", "career launch tech initiative", "synergisticit",
    "careerwellness", "edurech tech workforce",

    # Generic / unverifiable / manual-verification-required names
    "tech consulting", "open", "open healthcare", "wd", "north", "meridian",
    "soda", "prediction", "stealth startup", "practice & potential",
    "wayfinder solutions", "rk infotech", "digital kings networking",
    "maximatek", "neotech global", "cerebrone.ai", "cerebrone", "centervox",
    "o2 ai", "tpmai", "v4d", "geosnake", "aeyesky", "techvora", "valorantum",
    "seosaph-infotech", "seosaph infotech", "xaxis solutions", "eclipsos",
    "astay", "happy global", "medlaunch concepts", "metrix it solutions",
    "rs global services", "helfen company", "bigdatacorp", "staffpulse technologies",
    "subcontractorhub",
    "global trade integration", "le cercle des juristes en droit immobilier d'alsace",
    "aemtc", "genopsy reseau", "somarail reseau", "cesuga", "ef business school",
    "stpi",
}

# Substrings that reliably indicate a staffing/recruiting/consulting middleman,
# to catch name variants not covered by the exact list above.
EXCLUDED_COMPANY_KEYWORDS = {
    "staffing", "recruiting", "recruitment", "recruiters",
    "talent partners", "talent acquisition", "workforce solutions",
    "consulting group", "consulting solutions", "placement program",
    "placement agency", "technical talent",
}


def _normalize_company(company: str) -> str:
    name = company.lower().strip().replace(",", "")
    for suffix in (" inc.", " inc", " llc", " corp.", " corp", " ltd.", " ltd",
                   " co.", " pvt ltd", " pvt. ltd.", " limited", " corporation"):
        if name.endswith(suffix):
            name = name[: -len(suffix)].strip()
    return name


def is_excluded_by_company(company: str) -> bool:
    name = _normalize_company(company)
    if name in EXCLUDED_COMPANIES:
        return True
    return any(kw in name for kw in EXCLUDED_COMPANY_KEYWORDS)


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
