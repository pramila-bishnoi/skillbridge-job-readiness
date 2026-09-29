/**
 * TypeScript mirror of the FastAPI contract.
 *
 * These enums are the ONE place the backend's controlled vocabularies are
 * repeated on the frontend (project rule R2). If `app/models/enums.py` changes,
 * this file changes in the same commit — nowhere else should contain a string
 * literal such as 'INTERVIEW'.
 */

export const EmploymentType = {
  FULL_TIME: "FULL_TIME",
  PART_TIME: "PART_TIME",
  CONTRACT: "CONTRACT",
  INTERNSHIP: "INTERNSHIP",
} as const;
export type EmploymentType =
  (typeof EmploymentType)[keyof typeof EmploymentType];

export const EMPLOYMENT_TYPE_LABELS: Record<EmploymentType, string> = {
  FULL_TIME: "Full time",
  PART_TIME: "Part time",
  CONTRACT: "Contract",
  INTERNSHIP: "Internship",
};

export const ApplicationStatus = {
  APPLIED: "APPLIED",
  SCREENING: "SCREENING",
  INTERVIEW: "INTERVIEW",
  SELECTED: "SELECTED",
  REJECTED: "REJECTED",
} as const;
export type ApplicationStatus =
  (typeof ApplicationStatus)[keyof typeof ApplicationStatus];

export const APPLICATION_STATUS_LABELS: Record<ApplicationStatus, string> = {
  APPLIED: "Applied",
  SCREENING: "Screening",
  INTERVIEW: "Interview",
  SELECTED: "Selected",
  REJECTED: "Not selected",
};

/** The candidate-facing explanation shown on the tracking page. */
export const APPLICATION_STATUS_HELP: Record<ApplicationStatus, string> = {
  APPLIED: "Your application has been received and is waiting to be reviewed.",
  SCREENING: "A recruiter is reviewing your profile against the role.",
  INTERVIEW: "You have progressed to the interview stage.",
  SELECTED:
    "You have been selected. The team will be in touch about next steps.",
  REJECTED:
    "This application was not taken forward. Other roles remain open to you.",
};

export const PIPELINE_ORDER: ApplicationStatus[] = [
  "APPLIED",
  "SCREENING",
  "INTERVIEW",
  "SELECTED",
];

export type JobSort = "newest" | "oldest" | "title_asc" | "title_desc";

export interface Paginated<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  pages: number;
}

export interface JobSummary {
  id: number;
  job_code: string;
  title: string;
  department: string;
  location: string;
  employment_type: EmploymentType;
  experience_required: string;
  is_active: boolean;
  created_at: string;
  summary: string;
}

export interface AdminJobSummary extends JobSummary {
  application_count: number;
}

export interface JobDetail {
  id: number;
  job_code: string;
  title: string;
  department: string;
  location: string;
  employment_type: EmploymentType;
  description: string;
  responsibilities: string;
  skills: string;
  experience_required: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface JobFilterOptions {
  departments: string[];
  locations: string[];
  employment_types: EmploymentType[];
  total_active_jobs: number;
}

export interface JobPayload {
  title: string;
  department: string;
  location: string;
  employment_type: EmploymentType;
  description: string;
  responsibilities: string;
  skills: string;
  experience_required: string;
  is_active?: boolean;
}

export interface ApplicationCreated {
  success: boolean;
  application_code: string;
  job_title: string;
  status: ApplicationStatus;
  resume_uploaded: boolean;
  submitted_at: string;
  message: string;
}

export interface ApplicationTracking {
  application_code: string;
  job_title: string;
  job_code: string;
  status: ApplicationStatus;
  submitted_at: string;
  last_updated_at: string;
}

export interface ApplicationAdminSummary {
  id: number;
  application_code: string;
  name: string;
  email: string;
  phone: string;
  experience: string;
  status: ApplicationStatus;
  job_id: number;
  job_title: string;
  job_code: string;
  has_resume: boolean;
  match_score: number | null;
  match_terms: string | null;
  created_at: string;
  updated_at: string;
}

export interface ApplicationAdminDetail extends ApplicationAdminSummary {
  profile_url: string | null;
  cover_note: string | null;
  admin_notes: string | null;
  allowed_next_statuses: ApplicationStatus[];
}

export interface ResumeDownload {
  url: string;
  expires_in_seconds: number;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  expires_in_seconds: number;
  admin_email: string;
}

export interface AdminProfile {
  id: number;
  email: string;
  full_name: string | null;
  is_active: boolean;
}

export interface DashboardStats {
  active_jobs: number;
  total_jobs: number;
  total_applications: number;
  interviews: number;
  selected: number;
  rejected: number;
  applications_by_status: { status: ApplicationStatus; count: number }[];
  applications_by_department: { department: string; count: number }[];
  with_resume: number;
  without_resume: number;
  resume_rate: number;
  scored_applications: number;
  average_match_score: number | null;
  screening_rate: number;
  interview_rate: number;
  hire_rate: number;
  applications_by_location: { location: string; count: number }[];
  match_score_buckets: { label: string; count: number }[];
  applications_last_14_days: { day: string; count: number }[];
  recent_applications: {
    id: number;
    application_code: string;
    name: string;
    job_title: string;
    status: ApplicationStatus;
    created_at: string;
    match_score: number | null;
  }[];
  top_matches: {
    id?: number;
    application_code: string;
    name: string;
    job_title: string;
    status: ApplicationStatus;
    created_at: string;
    match_score: number | null;
  }[];
}

/** How a normalized skill was identified — kept for explainability. */
export type SkillMatchType = "CANONICAL_NAME" | "ALIAS";

export type JobRequirementType = "REQUIRED" | "PREFERRED";

/** One canonical skill a student's resume evidenced (Phase 2 skill
 * normalization), with the original text that triggered the match. */
export interface StudentSkill {
  skill_id: number;
  name: string;
  category: string | null;
  matched_text: string;
  match_type: SkillMatchType;
}

export interface StudentProfile {
  id: number;
  name: string;
  email: string;
  education: string | null;
  skills: string | null;
  projects: string | null;
  experience: string | null;
  resume_uploaded: boolean;
  resume_filename: string | null;
  extracted_skills: StudentSkill[];
  created_at: string;
  updated_at: string;
}

export interface StudentProfilePayload {
  name: string;
  email: string;
  education: string;
  skills: string;
  projects: string;
  experience: string;
}

export interface StudentProfileCreated {
  profile: StudentProfile;
  access_token: string;
  token_type: string;
  expires_in_seconds: number;
}

/** One canonical skill a saved job description evidences (Phase 3), with the
 * same matched-text/match-type explainability as a student's own skills. */
export interface JobRequirementSkill {
  skill_id: number;
  name: string;
  category: string | null;
  matched_text: string;
  match_type: SkillMatchType;
}

export interface JobProfileCreatePayload {
  title: string;
  company?: string | null;
  description: string;
  // Populated when this job was saved from a "Import from Job URL" preview;
  // omitted (all undefined) for a manually pasted description.
  source_url?: string | null;
  location?: string | null;
  employment_type?: string | null;
  compensation?: string | null;
  posted_date?: string | null;
}

/** List-view shape — no raw description, just counts. */
export interface JobProfileSummary {
  id: number;
  title: string;
  company: string | null;
  experience_required: string | null;
  required_skill_count: number;
  preferred_skill_count: number;
  created_at: string;
  updated_at: string;
}

export interface JobProfileDetail {
  id: number;
  title: string;
  company: string | null;
  description: string;
  experience_required: string | null;
  experience_evidence: string | null;
  required_skills: JobRequirementSkill[];
  preferred_skills: JobRequirementSkill[];
  source_url: string | null;
  location: string | null;
  employment_type: string | null;
  compensation: string | null;
  posted_date: string | null;
  created_at: string;
  updated_at: string;
}

/** "Import from Job URL" preview — nothing is saved until the student
 * confirms it via the existing job-create call. */
export interface JobUrlImportPreview {
  source_url: string;
  extraction_method: "JSON_LD" | "HTML_FALLBACK";
  title: string | null;
  company: string | null;
  location: string | null;
  employment_type: string | null;
  compensation: string | null;
  posted_date: string | null;
  description: string;
  experience_required: string | null;
  experience_evidence: string | null;
  required_skills: JobRequirementSkill[];
  preferred_skills: JobRequirementSkill[];
  warnings: string[];
}

/** How one job skill compares to the student's own normalized skills
 * (Phase 4). "RELATED" is reported only when an explicit relationship was
 * seeded — it is never treated as satisfying the requirement. */
export type SkillGapType =
  | "MATCHED"
  | "MISSING_REQUIRED"
  | "MISSING_PREFERRED"
  | "RELATED";

export type SkillGapImportance = "HIGH" | "MEDIUM" | "LOW";

/** One row of the per-skill breakdown behind a readiness analysis — the same
 * shape backs the matched/missing/gaps views, just filtered differently. */
export interface SkillGap {
  skill_id: number;
  name: string;
  category: string | null;
  requirement_type: JobRequirementType;
  gap_type: SkillGapType;
  importance: SkillGapImportance;
  evidence: string;
  related_to_skill_name: string | null;
}

export interface MatchAnalysisDetail {
  id: number;
  job_profile_id: number;
  job_title: string;

  readiness_score: number;
  score_version: string;

  required_skill_coverage: number;
  required_matched_count: number;
  required_total_count: number;

  preferred_skill_coverage: number;
  preferred_matched_count: number;
  preferred_total_count: number;

  experience_score: number;
  experience_evidence: string;

  text_similarity_score: number;
  text_similarity_terms: string | null;

  matched_skills: SkillGap[];
  missing_skills: SkillGap[];
  skill_gaps: SkillGap[];

  created_at: string;
  updated_at: string;
}

/** A student's own self-reported progress on one preparation item (Phase 5).
 * Only changes via the status-update call — regenerating the plan never
 * resets it for a skill that is still a gap. */
export type PreparationItemStatus = "NOT_STARTED" | "IN_PROGRESS" | "COMPLETED";

export interface PreparationItem {
  id: number;
  skill_id: number;
  name: string;
  category: string | null;
  requirement_type: JobRequirementType;
  gap_type: SkillGapType;
  priority: SkillGapImportance;
  reason: string;
  learning_focus: string;
  status: PreparationItemStatus;
}

export interface PreparationPlanDetail {
  id: number;
  job_profile_id: number;
  job_title: string;
  match_analysis_id: number;
  readiness_score: number;

  total_items: number;
  completed_items: number;
  in_progress_items: number;
  not_started_items: number;
  progress_percent: number;

  items: PreparationItem[];

  created_at: string;
  updated_at: string;
}

/** Why one interview question was generated (Phase 6). */
export type InterviewCategory =
  | "TECHNICAL"
  | "SKILL_GAP"
  | "RESUME_PROJECT"
  | "ROLE_CONCEPT";

export type InterviewDifficulty = "EASY" | "MEDIUM" | "HARD";

export interface InterviewQuestion {
  id: number;
  question: string;
  category: InterviewCategory;
  related_skill_name: string | null;
  difficulty: InterviewDifficulty;
  reason: string;
  completed: boolean;
}

export interface InterviewPrepDetail {
  job_profile_id: number;
  job_title: string;
  match_analysis_id: number;

  total_questions: number;
  completed_questions: number;
  progress_percent: number;

  questions: InterviewQuestion[];
}

/** One job's readiness compared side-by-side with the others (Phase 7). */
export interface JobComparisonEntry {
  job_profile_id: number;
  title: string;
  company: string | null;
  readiness_score: number;
  required_skill_coverage: number;
  preferred_skill_coverage: number;
  matched_skills: string[];
  missing_skills: string[];
  unique_missing_skills: string[];
}

export interface JobComparisonResult {
  jobs: JobComparisonEntry[];
  common_skills: string[];
  common_missing_skills: string[];
}

export type SkillProgressStatus = "NOT_STARTED" | "LEARNING" | "PRACTICED" | "CONFIDENT";

export interface SkillProgressEntry {
  skill_id: number;
  name: string;
  category: string | null;
  status: SkillProgressStatus;
  updated_at: string;
}

export interface SkillCatalogEntry {
  skill_id: number;
  name: string;
  category: string | null;
}

export interface ReadinessSummaryEntry {
  job_profile_id: number;
  title: string;
  readiness_score: number;
}

export interface StudentDashboardSummary {
  tracked_skills_count: number;
  not_started_count: number;
  learning_count: number;
  practiced_count: number;
  confident_count: number;

  analyzed_jobs_count: number;
  average_readiness_score: number | null;
  best_readiness_job: ReadinessSummaryEntry | null;

  recent_skill_progress: SkillProgressEntry[];
}

/** The error envelope every failing API call returns. */
export interface ApiErrorBody {
  success: false;
  error: {
    code: string;
    message: string;
    details?: { fields?: Record<string, string>; job_profile_ids?: number[] };
  };
  request_id: string;
}
