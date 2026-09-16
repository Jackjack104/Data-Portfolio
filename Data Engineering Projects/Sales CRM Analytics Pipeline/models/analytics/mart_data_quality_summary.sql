select
    'crm_companies'::text as quality_metric,
    count(*)::numeric as metric_value
from {{ ref('stg_crm_companies') }}

union all

select
    'erp_customers'::text,
    count(*)::numeric
from {{ ref('stg_erp_customers') }}

union all

select
    'matched_crm_companies'::text,
    count(*)::numeric
from {{ ref('int_company_matches') }}

union all

select
    'unmatched_crm_companies'::text,
    count(*)::numeric
from {{ ref('dim_customer') }}
where match_method = 'unmatched_crm'

union all

select
    'rejected_source_records'::text,
    count(*)::numeric
from {{ source('audit', 'rejected_records') }}

union all

select
    'successful_pipeline_runs'::text,
    count(*)::numeric
from {{ source('audit', 'pipeline_runs') }}
where status = 'succeeded'
