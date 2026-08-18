from sqladmin import ModelView
from app.models.user import User
from app.models.service import ServiceCategory, Service, TechStack
from app.models.case_study import Industry, CaseStudy, CaseStudyMetric
from app.models.talent import TalentRole
from app.models.social_proof import Testimonial, PressCoverage, CompanyStat
from app.models.inquiry import ContactInquiry
from app.models.career import JobPosting, JobApplication


# ------------------ User Administration ------------------ #
class UserAdmin(ModelView, model=User):
    name = "User"
    name_plural = "Users & Staff"
    icon = "fa-solid fa-users-gear"
    category = "Access Management"

    column_list = [
        User.id,
        User.email,
        User.full_name,
        User.role,
        User.is_active,
        User.is_superuser,
        User.created_at,
    ]
    column_searchable_list = [User.email, User.full_name]
    column_sortable_list = [User.id, User.email, User.role, User.created_at]
    column_filters = [User.role, User.is_active, User.is_superuser]
    form_excluded_columns = [User.created_at, User.updated_at]


# ------------------ Services & Technology ------------------ #
class ServiceCategoryAdmin(ModelView, model=ServiceCategory):
    name = "Service Category"
    name_plural = "Service Categories"
    icon = "fa-solid fa-layer-group"
    category = "Services Engine"

    column_list = [
        ServiceCategory.id,
        ServiceCategory.name,
        ServiceCategory.slug,
        ServiceCategory.display_order,
        ServiceCategory.is_active,
    ]
    column_searchable_list = [ServiceCategory.name, ServiceCategory.slug]
    column_sortable_list = [ServiceCategory.display_order, ServiceCategory.name]
    column_filters = [ServiceCategory.is_active]


class ServiceAdmin(ModelView, model=Service):
    name = "Service"
    name_plural = "Services"
    icon = "fa-solid fa-cubes"
    category = "Services Engine"

    column_list = [
        Service.id,
        Service.title,
        Service.slug,
        Service.category,
        Service.featured,
        Service.is_active,
        Service.display_order,
    ]
    column_searchable_list = [Service.title, Service.slug, Service.short_description]
    column_sortable_list = [Service.display_order, Service.title, Service.featured]
    column_filters = [Service.category, Service.featured, Service.is_active]


class TechStackAdmin(ModelView, model=TechStack):
    name = "Tech Stack"
    name_plural = "Tech Stacks"
    icon = "fa-solid fa-code-fork"
    category = "Services Engine"

    column_list = [
        TechStack.id,
        TechStack.name,
        TechStack.slug,
        TechStack.category,
        TechStack.is_active,
    ]
    column_searchable_list = [TechStack.name, TechStack.category]
    column_sortable_list = [TechStack.category, TechStack.name]
    column_filters = [TechStack.category, TechStack.is_active]


# ------------------ Portfolio & Case Studies ------------------ #
class IndustryAdmin(ModelView, model=Industry):
    name = "Industry"
    name_plural = "Industries"
    icon = "fa-solid fa-industry"
    category = "Portfolio & Case Studies"

    column_list = [Industry.id, Industry.name, Industry.slug]
    column_searchable_list = [Industry.name, Industry.slug]


class CaseStudyAdmin(ModelView, model=CaseStudy):
    name = "Case Study"
    name_plural = "Case Studies"
    icon = "fa-solid fa-briefcase"
    category = "Portfolio & Case Studies"

    column_list = [
        CaseStudy.id,
        CaseStudy.title,
        CaseStudy.client_name,
        CaseStudy.industry,
        CaseStudy.featured,
        CaseStudy.is_published,
        CaseStudy.display_order,
    ]
    column_searchable_list = [CaseStudy.title, CaseStudy.client_name, CaseStudy.slug]
    column_sortable_list = [CaseStudy.display_order, CaseStudy.created_at, CaseStudy.featured]
    column_filters = [CaseStudy.industry, CaseStudy.featured, CaseStudy.is_published]


class CaseStudyMetricAdmin(ModelView, model=CaseStudyMetric):
    name = "Case Study Metric"
    name_plural = "Case Study Metrics"
    icon = "fa-solid fa-chart-line"
    category = "Portfolio & Case Studies"

    column_list = [
        CaseStudyMetric.id,
        CaseStudyMetric.case_study,
        CaseStudyMetric.label,
        CaseStudyMetric.value,
        CaseStudyMetric.display_order,
    ]
    column_searchable_list = [CaseStudyMetric.label, CaseStudyMetric.value]
    column_sortable_list = [CaseStudyMetric.display_order]


# ------------------ Staff Augmentation ------------------ #
class TalentRoleAdmin(ModelView, model=TalentRole):
    name = "Talent Role"
    name_plural = "Talent & Augmentation"
    icon = "fa-solid fa-user-tie"
    category = "Talent Engine"

    column_list = [
        TalentRole.id,
        TalentRole.title,
        TalentRole.department,
        TalentRole.experience_level,
        TalentRole.availability,
        TalentRole.hourly_rate_estimate,
        TalentRole.is_active,
    ]
    column_searchable_list = [TalentRole.title, TalentRole.department]
    column_sortable_list = [TalentRole.display_order, TalentRole.title]
    column_filters = [TalentRole.department, TalentRole.is_active]


# ------------------ Social Proof & Press ------------------ #
class TestimonialAdmin(ModelView, model=Testimonial):
    name = "Testimonial"
    name_plural = "Testimonials"
    icon = "fa-solid fa-quote-left"
    category = "Social Proof & Media"

    column_list = [
        Testimonial.id,
        Testimonial.client_name,
        Testimonial.client_company,
        Testimonial.rating,
        Testimonial.featured,
        Testimonial.is_active,
    ]
    column_searchable_list = [Testimonial.client_name, Testimonial.client_company]
    column_sortable_list = [Testimonial.rating, Testimonial.display_order]
    column_filters = [Testimonial.rating, Testimonial.featured, Testimonial.is_active]


class PressCoverageAdmin(ModelView, model=PressCoverage):
    name = "Press Coverage"
    name_plural = "Press Coverage"
    icon = "fa-solid fa-newspaper"
    category = "Social Proof & Media"

    column_list = [
        PressCoverage.id,
        PressCoverage.publisher_name,
        PressCoverage.headline,
        PressCoverage.published_date,
        PressCoverage.featured,
        PressCoverage.is_active,
    ]
    column_searchable_list = [PressCoverage.publisher_name, PressCoverage.headline]
    column_sortable_list = [PressCoverage.published_date, PressCoverage.display_order]
    column_filters = [PressCoverage.featured, PressCoverage.is_active]


class CompanyStatAdmin(ModelView, model=CompanyStat):
    name = "Company Stat"
    name_plural = "Company Stats"
    icon = "fa-solid fa-calculator"
    category = "Social Proof & Media"

    column_list = [
        CompanyStat.id,
        CompanyStat.label,
        CompanyStat.metric_value,
        CompanyStat.is_active,
        CompanyStat.display_order,
    ]
    column_searchable_list = [CompanyStat.label, CompanyStat.metric_value]
    column_sortable_list = [CompanyStat.display_order]


# ------------------ Inquiries & CRM ------------------ #
class ContactInquiryAdmin(ModelView, model=ContactInquiry):
    name = "Contact Inquiry"
    name_plural = "Contact Inquiries (Leads)"
    icon = "fa-solid fa-envelope-open-text"
    category = "CRM & Leads"

    column_list = [
        ContactInquiry.id,
        ContactInquiry.full_name,
        ContactInquiry.email,
        ContactInquiry.company_name,
        ContactInquiry.service_interest,
        ContactInquiry.status,
        ContactInquiry.created_at,
    ]
    column_searchable_list = [ContactInquiry.full_name, ContactInquiry.email, ContactInquiry.company_name]
    column_sortable_list = [ContactInquiry.created_at, ContactInquiry.status]
    column_filters = [ContactInquiry.status, ContactInquiry.service_interest]


# ------------------ Careers & Recruitment ------------------ #
class JobPostingAdmin(ModelView, model=JobPosting):
    name = "Job Posting"
    name_plural = "Job Openings"
    icon = "fa-solid fa-address-card"
    category = "Recruitment & HR"

    column_list = [
        JobPosting.id,
        JobPosting.title,
        JobPosting.department,
        JobPosting.location_type,
        JobPosting.employment_type,
        JobPosting.is_active,
        JobPosting.deadline,
    ]
    column_searchable_list = [JobPosting.title, JobPosting.department]
    column_sortable_list = [JobPosting.created_at, JobPosting.display_order]
    column_filters = [JobPosting.department, JobPosting.location_type, JobPosting.is_active]


class JobApplicationAdmin(ModelView, model=JobApplication):
    name = "Job Application"
    name_plural = "Candidate Applications"
    icon = "fa-solid fa-file-signature"
    category = "Recruitment & HR"

    column_list = [
        JobApplication.id,
        JobApplication.candidate_name,
        JobApplication.email,
        JobApplication.job_posting,
        JobApplication.status,
        JobApplication.years_of_experience,
        JobApplication.created_at,
    ]
    column_searchable_list = [JobApplication.candidate_name, JobApplication.email]
    column_sortable_list = [JobApplication.created_at, JobApplication.status]
    column_filters = [JobApplication.status, JobApplication.job_posting]
