create schema if not exists raw;
create schema if not exists audit;
create schema if not exists staging;
create schema if not exists intermediate;
create schema if not exists analytics;

create table if not exists audit.pipeline_runs (
    run_id uuid primary key,
    started_at timestamptz not null default current_timestamp,
    completed_at timestamptz,
    status text not null check (status in ('running', 'succeeded', 'failed')),
    input_path text not null,
    batches_processed integer not null default 0,
    loaded_records integer not null default 0,
    duplicate_records integer not null default 0,
    rejected_records integer not null default 0,
    error_message text
);

create table if not exists audit.rejected_records (
    reject_id bigint generated always as identity primary key,
    run_id uuid not null references audit.pipeline_runs(run_id),
    batch_id text not null,
    source_name text not null,
    source_file text not null,
    source_record_id text,
    rejection_reason text not null,
    raw_payload jsonb not null,
    rejected_at timestamptz not null default current_timestamp
);

create table if not exists raw.crm_companies (
    raw_id bigint generated always as identity primary key,
    company_id text not null,
    company_name text not null,
    domain text,
    phone text,
    address text,
    city text,
    state text,
    postal_code text,
    owner_id text,
    erp_customer_id text,
    source_updated_at timestamptz not null,
    batch_id text not null,
    source_file text not null,
    record_hash text not null,
    ingested_at timestamptz not null default current_timestamp,
    unique (company_id, record_hash)
);

create table if not exists raw.crm_contacts (
    raw_id bigint generated always as identity primary key,
    contact_id text not null,
    company_id text,
    first_name text,
    last_name text,
    email text not null,
    phone text,
    job_title text,
    source_updated_at timestamptz not null,
    batch_id text not null,
    source_file text not null,
    record_hash text not null,
    ingested_at timestamptz not null default current_timestamp,
    unique (contact_id, record_hash)
);

create table if not exists raw.erp_customers (
    raw_id bigint generated always as identity primary key,
    customer_id text not null,
    company_name text not null,
    email_domain text,
    address text,
    city text,
    state text,
    postal_code text,
    is_active boolean not null,
    source_updated_at timestamptz not null,
    batch_id text not null,
    source_file text not null,
    record_hash text not null,
    ingested_at timestamptz not null default current_timestamp,
    unique (customer_id, record_hash)
);

create table if not exists raw.erp_orders (
    raw_id bigint generated always as identity primary key,
    order_id text not null,
    customer_id text not null,
    order_date date not null,
    product_line text not null,
    order_status text not null,
    order_amount numeric(12, 2) not null,
    source_updated_at timestamptz not null,
    batch_id text not null,
    source_file text not null,
    record_hash text not null,
    ingested_at timestamptz not null default current_timestamp,
    unique (order_id, record_hash)
);

create index if not exists ix_raw_crm_companies_company_id
    on raw.crm_companies(company_id);
create index if not exists ix_raw_crm_contacts_contact_id
    on raw.crm_contacts(contact_id);
create index if not exists ix_raw_erp_customers_customer_id
    on raw.erp_customers(customer_id);
create index if not exists ix_raw_erp_orders_order_id
    on raw.erp_orders(order_id);
create index if not exists ix_raw_erp_orders_customer_id
    on raw.erp_orders(customer_id);
