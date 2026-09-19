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