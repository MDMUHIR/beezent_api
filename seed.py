import asyncio
from datetime import date, datetime, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal, async_engine
from app.core.security import get_password_hash
from app.models.base import Base
from app.models.career import ApplicationStatus, JobApplication, JobPosting
from app.models.case_study import CaseStudy, CaseStudyMetric, Industry
from app.models.inquiry import ContactInquiry, InquiryStatus
from app.models.service import Service, ServiceCategory, TechStack
from app.models.social_proof import CompanyStat, PressCoverage, Testimonial
from app.models.talent import TalentRole
from app.models.user import User, UserRole


async def seed_database():
    print("🌱 Initializing database schema...")
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as db:
        print("👤 Checking and seeding administrative users...")
        # 1. Super Admin
        admin_email = settings.FIRST_SUPERUSER_EMAIL
        existing_admin = (await db.execute(select(User).where(User.email == admin_email))).scalar_one_or_none()

        if not existing_admin:
            super_admin = User(
                email=admin_email,
                hashed_password=get_password_hash(settings.FIRST_SUPERUSER_PASSWORD),
                full_name="Alex Vance (Super Admin)",
                role=UserRole.SUPER_ADMIN,
                is_active=True,
                is_superuser=True,
            )
            editor_user = User(
                email="editor@agency.com",
                hashed_password=get_password_hash("editor123"),
                full_name="Sarah Jenkins (Senior Editor)",
                role=UserRole.EDITOR,
                is_active=True,
                is_superuser=False,
            )
            db.add_all([super_admin, editor_user])
            await db.commit()
            print(f"✅ Created super-admin: {admin_email} / {settings.FIRST_SUPERUSER_PASSWORD}")
            print("✅ Created staff editor: editor@agency.com / editor123")
        else:
            print(f"ℹ️ Super-admin {admin_email} already exists.")

        # Check if already seeded data
        existing_categories = (await db.execute(select(ServiceCategory))).scalars().all()
        if len(existing_categories) > 0:
            print("ℹ️ Sample agency data already present. Skipping dataset re-seed.")
            return

        print("📦 Seeding Tech Stacks...")
        tech_stacks = [
            TechStack(name="Python", slug="python", category="Backend", icon_url="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/python/python-original.svg"),
            TechStack(name="FastAPI", slug="fastapi", category="Backend", icon_url="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/fastapi/fastapi-original.svg"),
            TechStack(name="PyTorch", slug="pytorch", category="AI / ML", icon_url="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/pytorch/pytorch-original.svg"),
            TechStack(name="LangChain", slug="langchain", category="AI / ML", icon_url="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=80"),
            TechStack(name="Next.js", slug="nextjs", category="Frontend", icon_url="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/nextjs/nextjs-original.svg"),
            TechStack(name="React", slug="react", category="Frontend", icon_url="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/react/react-original.svg"),
            TechStack(name="TypeScript", slug="typescript", category="Frontend", icon_url="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/typescript/typescript-original.svg"),
            TechStack(name="Flutter", slug="flutter", category="Mobile", icon_url="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/flutter/flutter-original.svg"),
            TechStack(name="Swift", slug="swift", category="Mobile", icon_url="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/swift/swift-original.svg"),
            TechStack(name="PostgreSQL", slug="postgresql", category="Database", icon_url="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/postgresql/postgresql-original.svg"),
            TechStack(name="Docker", slug="docker", category="DevOps", icon_url="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/docker/docker-original.svg"),
            TechStack(name="Kubernetes", slug="kubernetes", category="DevOps", icon_url="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/kubernetes/kubernetes-plain.svg"),
            TechStack(name="Unreal Engine", slug="unreal-engine", category="Game & 3D", icon_url="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/unrealengine/unrealengine-original.svg"),
            TechStack(name="Solana & Rust", slug="solana-rust", category="Web3", icon_url="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/rust/rust-plain.svg"),
        ]
        db.add_all(tech_stacks)
        await db.flush()

        print("🗂️ Seeding Service Categories & Services...")
        cat_ai = ServiceCategory(
            name="AI & Intelligent Automation",
            slug="ai-intelligent-automation",
            description="Agentic workflows, fine-tuned LLM architectures, predictive computer vision, and cognitive decision systems.",
            icon="BrainCircuit",
            display_order=1,
            is_active=True,
        )
        cat_software = ServiceCategory(
            name="Enterprise Custom Software",
            slug="enterprise-custom-software",
            description="Mission-critical cloud-native platforms, high-throughput microservices, and modern headless architectures.",
            icon="Layers",
            display_order=2,
            is_active=True,
        )
        cat_mobile = ServiceCategory(
            name="Mobile Apps & Cross-Platform",
            slug="mobile-apps-cross-platform",
            description="Native iOS/Android, Flutter, and React Native mobile apps engineered for ultra-responsive engagement.",
            icon="Smartphone",
            display_order=3,
            is_active=True,
        )
        cat_interactive = ServiceCategory(
            name="Interactive 3D, AR/VR & Games",
            slug="interactive-3d-ar-vr-games",
            description="Unreal Engine 5 pipelines, Unity multi-platform games, WebGL immersive spaces, and virtual simulations.",
            icon="Gamepad2",
            display_order=4,
            is_active=True,
        )
        db.add_all([cat_ai, cat_software, cat_mobile, cat_interactive])
        await db.flush()

        # Services
        s1 = Service(
            category_id=cat_ai.id,
            title="Agentic AI & Custom LLM Development",
            slug="agentic-ai-custom-llm-development",
            short_description="Deploy domain-specialized multi-agent AI systems with enterprise RAG and autonomous execution.",
            content="""# Autonomous Multi-Agent AI Architecture
We build secure, on-premise and private cloud AI agents that autonomously execute multi-step business workflows.

### What We Deliver:
- **Enterprise Retrieval-Augmented Generation (RAG)**: Hybrid dense & sparse vector search over millions of internal documents with sub-100ms latency.
- **Agent Tool Calling & Orchestration**: Deterministic execution frameworks using LangGraph and AutoGen.
- **Fine-Tuning & Quantization**: Custom LoRA/QLoRA fine-tuning for domain jargon, compliance, and cost efficiency.""",
            icon_url="https://images.unsplash.com/photo-1677442136019-21780efad99a?w=400",
            featured=True,
            display_order=1,
            is_active=True,
            tech_stacks=[tech_stacks[0], tech_stacks[1], tech_stacks[2], tech_stacks[3]],
        )

        s2 = Service(
            category_id=cat_software.id,
            title="High-Scale Cloud Microservices & Headless APIs",
            slug="high-scale-cloud-microservices",
            short_description="Fault-tolerant backend architectures capable of sustaining 100k+ concurrent requests with zero downtime.",
            content="""# Mission-Critical Scalability
Engineered from the ground up for high concurrency, event-driven scalability, and complete API reliability.""",
            icon_url="https://images.unsplash.com/photo-1558494949-ef010cbdcc31?w=400",
            featured=True,
            display_order=2,
            is_active=True,
            tech_stacks=[tech_stacks[0], tech_stacks[1], tech_stacks[9], tech_stacks[10], tech_stacks[11]],
        )

        s3 = Service(
            category_id=cat_mobile.id,
            title="Next-Gen Cross-Platform Mobile Apps",
            slug="next-gen-cross-platform-mobile-apps",
            short_description="Fluid, reactive 60fps mobile experiences built with Flutter and Native Swift/Kotlin.",
            content="""# World-Class Mobile Engineering
Deliver 5-star mobile applications on App Store and Google Play with unified codebases.""",
            icon_url="https://images.unsplash.com/photo-1512941937669-90a1b58e7e9c?w=400",
            featured=True,
            display_order=3,
            is_active=True,
            tech_stacks=[tech_stacks[7], tech_stacks[8]],
        )
        db.add_all([s1, s2, s3])
        await db.flush()

        print("🏢 Seeding Industries & Case Studies with Metrics...")
        ind_fintech = Industry(name="FinTech & Banking", slug="fintech-banking", description="High-frequency trading, fraud prevention & digital payments")
        ind_health = Industry(name="Healthcare & MedTech", slug="healthcare-medtech", description="HIPAA-compliant health cloud platforms and diagnostic AI")
        ind_ecommerce = Industry(name="E-Commerce & Retail", slug="ecommerce-retail", description="High-throughput headless commerce and personalization")
        db.add_all([ind_fintech, ind_health, ind_ecommerce])
        await db.flush()

        cs1 = CaseStudy(
            industry_id=ind_fintech.id,
            title="Autonomous Fraud Sentinel for Tier-1 Digital Bank",
            slug="autonomous-fraud-sentinel-digital-bank",
            client_name="FinGlobal Vault",
            client_logo_url="https://images.unsplash.com/photo-1559526324-4b87b5e36e44?w=120",
            summary="Engineered a real-time transaction streaming inference engine processing $12B+ in annual volume with sub-25ms latency.",
            challenge="Legacy rule-based fraud detection generated 18% false positive rate, causing customer churn and $4.2M in annual manual review overhead.",
            solution="Constructed an async streaming inference pipeline utilizing PyTorch graph neural networks and FastAPI async workers with Kafka queue ingestion.",
            result="Slashed false positives by 84% while intercepting 99.4% of unauthorized transactions in under 22 milliseconds.",
            cover_image_url="https://images.unsplash.com/photo-1563986768609-322da13575f3?w=800",
            live_url="https://finglobal-vault-demo.example.com",
            featured=True,
            is_published=True,
            display_order=1,
        )
        db.add(cs1)
        await db.flush()

        m1 = CaseStudyMetric(case_study_id=cs1.id, label="Fraud Prevention Accuracy", value="99.4%", description="Real-time precision score", display_order=1)
        m2 = CaseStudyMetric(case_study_id=cs1.id, label="Annual Cost Saved", value="$4.2M", description="Reduction in manual review ops", display_order=2)
        m3 = CaseStudyMetric(case_study_id=cs1.id, label="P99 Latency", value="22ms", description="Global streaming inference", display_order=3)
        db.add_all([m1, m2, m3])

        print("💼 Seeding Staff Augmentation & Talent Profiles...")
        t1 = TalentRole(
            title="Principal AI & LLM Systems Architect",
            slug="principal-ai-llm-systems-architect",
            department="AI & Machine Learning",
            experience_level="Principal (8+ yrs)",
            core_skills=["PyTorch", "LangGraph", "FastAPI", "Vector DBs", "CUDA Optimization", "vLLM"],
            short_description="Specializes in designing resilient multi-agent swarms, custom fine-tuning pipelines, and high-throughput model serving.",
            availability="Immediate (48 hrs)",
            hourly_rate_estimate="$95 - $130 / hr",
            is_active=True,
            display_order=1,
        )
        t2 = TalentRole(
            title="Senior Full Stack & Cloud Architect",
            slug="senior-full-stack-cloud-architect",
            department="Engineering",
            experience_level="Senior (6+ yrs)",
            core_skills=["Python", "FastAPI", "React", "Next.js", "Kubernetes", "PostgreSQL"],
            short_description="Expert in building microservice backends, real-time WebSockets, and high-concurrency headless platforms.",
            availability="1 Week",
            hourly_rate_estimate="$75 - $95 / hr",
            is_active=True,
            display_order=2,
        )
        db.add_all([t1, t2])

        print("🌟 Seeding Testimonials, Press, and Company Stats...")
        test1 = Testimonial(
            client_name="Jonathan Mercer",
            client_role="Chief Technology Officer",
            client_company="FinGlobal Vault",
            avatar_url="https://images.unsplash.com/photo-1534528741775-53994a69daeb?w=200",
            quote="Their engineering depth in FastAPI and distributed AI inference is unmatched. They delivered our core platform 6 weeks ahead of schedule.",
            rating=5,
            project_title="Realtime Fraud Engine",
            featured=True,
            is_active=True,
            display_order=1,
        )
        db.add(test1)

        press1 = PressCoverage(
            publisher_name="TechCrunch",
            publisher_logo_url="https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=150",
            headline="Agency Named Top Global Digital Engineering Firm for Next-Gen Enterprise AI",
            article_url="https://techcrunch.example.com/agency-award",
            excerpt="Recognized for exceptional engineering standards and breakthrough AI agent deployments.",
            published_date=date(2026, 4, 15),
            featured=True,
            is_active=True,
            display_order=1,
        )
        db.add(press1)

        stat1 = CompanyStat(label="Enterprise Projects Delivered", metric_value="250+", description="Across 14 countries", is_active=True, display_order=1)
        stat2 = CompanyStat(label="Client Retention Rate", metric_value="99.2%", description="Long-term agency partnerships", is_active=True, display_order=2)
        stat3 = CompanyStat(label="Senior Engineers & Tech Talent", metric_value="180+", description="100% in-house vetted", is_active=True, display_order=3)
        stat4 = CompanyStat(label="Client Value Created", metric_value="$500M+", description="Measurable ROI generated", is_active=True, display_order=4)
        db.add_all([stat1, stat2, stat3, stat4])

        print("📬 Seeding Contact Inquiries & Careers...")
        inq1 = ContactInquiry(
            full_name="Elena Rostova",
            email="elena.r@fintechnova.io",
            phone_number="+1 (555) 382-9912",
            company_name="Fintech Nova Labs",
            service_interest="AI & Intelligent Automation",
            budget_range="$50k - $100k",
            timeline="Next 30 days",
            message="We are looking for a senior agency team to architect an autonomous credit risk modeling engine with FastAPI and PyTorch.",
            status=InquiryStatus.NEW,
            internal_notes="High priority enterprise lead. Initial discovery call scheduled.",
        )
        db.add(inq1)

        job1 = JobPosting(
            title="Senior Python / FastAPI Backend Engineer",
            slug="senior-python-fastapi-backend-engineer",
            department="Engineering",
            location_type="Remote",
            location="Global Remote (UTC-5 to UTC+3)",
            employment_type="Full-Time",
            experience_level="Senior (5+ yrs)",
            salary_range="$90,000 - $130,000 / yr",
            summary="Lead the architectural design of high-throughput backend services and headless CMS integrations.",
            description="We are seeking an outstanding Senior Backend Engineer with deep mastery of Python 3.11+, FastAPI, SQLAlchemy 2.0, and PostgreSQL.",
            requirements=["5+ years Python development", "Expertise with async SQLAlchemy 2.0 and Alembic", "Proficiency with Docker and CI/CD pipelines"],
            responsibilities=["Design robust RESTful APIs", "Write high-coverage automated test suites", "Collaborate with frontend engineers on Next.js/Nuxt contracts"],
            perks=["100% Remote flexibility", "Health insurance", "Annual learning & conference stipend ($3,000)", "Modern hardware setup"],
            deadline=date(2026, 12, 31),
            is_active=True,
            display_order=1,
        )
        db.add(job1)
        await db.flush()

        app1 = JobApplication(
            job_posting_id=job1.id,
            candidate_name="David Chen",
            email="david.chen.dev@example.com",
            phone="+1 (555) 712-4491",
            linkedin_url="https://linkedin.com/in/david-chen-sample",
            portfolio_url="https://github.com/davidchen-sample",
            resume_url="https://storage.example.com/resumes/david-chen-resume.pdf",
            cover_letter="I have 6 years of experience building async FastAPI architectures with PostgreSQL and Alembic. I would love to contribute to your agency!",
            years_of_experience=6,
            status=ApplicationStatus.REVIEWING,
            admin_notes="Strong portfolio with production asyncpg and Docker experience.",
        )
        db.add(app1)

        await db.commit()
        print("🎉 Database successfully seeded with full agency test data!")


if __name__ == "__main__":
    asyncio.run(seed_database())
