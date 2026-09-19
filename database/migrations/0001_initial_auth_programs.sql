-- Rt scholarship platform: initial authentication and program schema.
-- SQLite-compatible SQL. Keep application authorization checks in the service layer too.

PRAGMA foreign_keys = ON;

CREATE TABLE roles (
    id TEXT PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    name TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'inactive', 'locked')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE user_roles (
    user_id TEXT NOT NULL,
    role_id TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, role_id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (role_id) REFERENCES roles (id) ON DELETE RESTRICT
);

CREATE TABLE scholarship_programs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'active', 'closed')),
    application_start_at TEXT,
    application_end_at TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        application_start_at IS NULL
        OR application_end_at IS NULL
        OR application_start_at <= application_end_at
    ),
    FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE TABLE fund_categories (
    id TEXT PRIMARY KEY,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category_type TEXT NOT NULL
        CHECK (category_type IN ('country', 'region', 'major', 'ministry')),
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE announcements (
    id TEXT PRIMARY KEY,
    program_id TEXT NOT NULL,
    title TEXT NOT NULL,
    target_description TEXT,
    selected_count INTEGER CHECK (selected_count IS NULL OR selected_count >= 0),
    payment_description TEXT,
    status TEXT NOT NULL DEFAULT 'draft'
        CHECK (status IN ('draft', 'open', 'closed', 'reviewing', 'finished')),
    fund_category_id TEXT,
    published_at TEXT,
    application_start_at TEXT,
    application_end_at TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK (
        application_start_at IS NULL
        OR application_end_at IS NULL
        OR application_start_at <= application_end_at
    ),
    FOREIGN KEY (program_id) REFERENCES scholarship_programs (id) ON DELETE CASCADE,
    FOREIGN KEY (fund_category_id) REFERENCES fund_categories (id) ON DELETE SET NULL,
    FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE TABLE applications (
    id TEXT PRIMARY KEY,
    applicant_id TEXT NOT NULL,
    announcement_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'submitted'
        CHECK (status IN ('draft', 'submitted', 'under_review', 'selected', 'rejected', 'withdrawn')),
    study_plan TEXT NOT NULL,
    financial_need TEXT NOT NULL,
    ministry_plan TEXT,
    submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (applicant_id, announcement_id),
    FOREIGN KEY (applicant_id) REFERENCES users (id) ON DELETE RESTRICT,
    FOREIGN KEY (announcement_id) REFERENCES announcements (id) ON DELETE RESTRICT
);

CREATE TABLE review_criteria (
    id TEXT PRIMARY KEY,
    announcement_id TEXT NOT NULL,
    code TEXT NOT NULL,
    name TEXT NOT NULL,
    max_score INTEGER NOT NULL CHECK (max_score > 0),
    required INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (announcement_id, code),
    FOREIGN KEY (announcement_id) REFERENCES announcements (id) ON DELETE CASCADE
);

CREATE TABLE review_assignments (
    id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL,
    reviewer_id TEXT NOT NULL,
    recused_at TEXT,
    recusal_reason TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (application_id, reviewer_id),
    FOREIGN KEY (application_id) REFERENCES applications (id) ON DELETE CASCADE,
    FOREIGN KEY (reviewer_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE TABLE reviews (
    id TEXT PRIMARY KEY,
    assignment_id TEXT NOT NULL,
    criterion_id TEXT NOT NULL,
    score INTEGER NOT NULL CHECK (score >= 0),
    comment TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (assignment_id, criterion_id),
    FOREIGN KEY (assignment_id) REFERENCES review_assignments (id) ON DELETE CASCADE,
    FOREIGN KEY (criterion_id) REFERENCES review_criteria (id) ON DELETE RESTRICT
);

CREATE TABLE followups (
    id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL,
    applicant_id TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'submitted',
    academic_update TEXT NOT NULL,
    ministry_update TEXT NOT NULL,
    evidence_note TEXT,
    submitted_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES applications (id) ON DELETE RESTRICT,
    FOREIGN KEY (applicant_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE TABLE finance_transactions (
    id TEXT PRIMARY KEY,
    transaction_date TEXT NOT NULL,
    transaction_type TEXT NOT NULL CHECK (transaction_type IN ('income', 'expense')),
    amount INTEGER NOT NULL CHECK (amount > 0),
    description TEXT NOT NULL,
    external_reference TEXT NOT NULL UNIQUE,
    source_filename TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (created_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE TABLE selections (
    id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL UNIQUE,
    applicant_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('selected', 'rejected')),
    amount INTEGER CHECK (amount IS NULL OR amount > 0),
    decided_by TEXT NOT NULL,
    decided_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES applications (id) ON DELETE RESTRICT,
    FOREIGN KEY (applicant_id) REFERENCES users (id) ON DELETE RESTRICT,
    FOREIGN KEY (decided_by) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE TABLE payments (
    id TEXT PRIMARY KEY,
    selection_id TEXT NOT NULL,
    amount INTEGER NOT NULL CHECK (amount > 0),
    status TEXT NOT NULL DEFAULT 'paid' CHECK (status IN ('planned', 'paid', 'failed')),
    payment_method TEXT NOT NULL,
    external_reference TEXT NOT NULL UNIQUE,
    paid_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    finance_transaction_id TEXT NOT NULL,
    FOREIGN KEY (selection_id) REFERENCES selections (id) ON DELETE RESTRICT,
    FOREIGN KEY (finance_transaction_id) REFERENCES finance_transactions (id) ON DELETE RESTRICT
);

CREATE TABLE application_documents (
    id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL,
    applicant_id TEXT NOT NULL,
    document_type TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    stored_filename TEXT NOT NULL UNIQUE,
    content_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (application_id) REFERENCES applications (id) ON DELETE CASCADE,
    FOREIGN KEY (applicant_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE TABLE followup_documents (
    id TEXT PRIMARY KEY,
    followup_id TEXT NOT NULL,
    applicant_id TEXT NOT NULL,
    document_type TEXT NOT NULL,
    original_filename TEXT NOT NULL,
    stored_filename TEXT NOT NULL UNIQUE,
    content_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (followup_id) REFERENCES followups (id) ON DELETE CASCADE,
    FOREIGN KEY (applicant_id) REFERENCES users (id) ON DELETE RESTRICT
);

-- Prayer requests are pastoral-care data only. There is intentionally no review
-- or score foreign key in this table.
CREATE TABLE prayer_requests (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    content TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'archived', 'deleted')),
    visibility TEXT NOT NULL DEFAULT 'pastoral'
        CHECK (visibility = 'pastoral'),
    retention_until TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE TABLE prayer_request_access_logs (
    id TEXT PRIMARY KEY,
    prayer_request_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    purpose TEXT NOT NULL
        CHECK (purpose IN ('intercessory_prayer', 'pastoral_care')),
    accessed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (prayer_request_id) REFERENCES prayer_requests (id) ON DELETE RESTRICT,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE RESTRICT
);

CREATE INDEX idx_user_roles_role_id ON user_roles (role_id);
CREATE INDEX idx_programs_status ON scholarship_programs (status);
CREATE INDEX idx_announcements_program_id ON announcements (program_id);
CREATE INDEX idx_announcements_status ON announcements (status);
CREATE INDEX idx_applications_applicant_id ON applications (applicant_id);
CREATE INDEX idx_applications_announcement_id ON applications (announcement_id);
CREATE INDEX idx_review_criteria_announcement_id ON review_criteria (announcement_id);
CREATE INDEX idx_review_assignments_reviewer_id ON review_assignments (reviewer_id);
CREATE INDEX idx_reviews_assignment_id ON reviews (assignment_id);
CREATE INDEX idx_followups_applicant_id ON followups (applicant_id);
CREATE INDEX idx_followups_application_id ON followups (application_id);
CREATE INDEX idx_finance_transactions_type ON finance_transactions (transaction_type);
CREATE INDEX idx_selections_applicant_id ON selections (applicant_id);
CREATE INDEX idx_payments_selection_id ON payments (selection_id);
CREATE INDEX idx_application_documents_application_id ON application_documents (application_id);
CREATE INDEX idx_followup_documents_followup_id ON followup_documents (followup_id);
CREATE INDEX idx_prayer_requests_user_id ON prayer_requests (user_id);
CREATE INDEX idx_prayer_access_logs_request_id
    ON prayer_request_access_logs (prayer_request_id);

INSERT INTO roles (id, code, name, description) VALUES
    ('role-admin', 'administrator', '관리자', '사용자와 기준정보를 관리한다.'),
    ('role-manager', 'program_manager', '사업 담당자', '사업, 공고, 심사 운영을 관리한다.'),
    ('role-reviewer', 'reviewer', '장학위원', '배정된 신청을 심사한다.'),
    ('role-ministry', 'ministry_worker', '사역 담당자', '중보기도와 목회적 돌봄을 담당한다.'),
    ('role-finance', 'finance', '지급 담당자', '기금과 지급 업무를 담당한다.'),
    ('role-applicant', 'applicant', '신청자', '본인의 신청과 기도제목을 관리한다.');