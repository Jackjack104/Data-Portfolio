with ranked as (
    select
        *,
        row_number() over (
            partition by contact_id
            order by source_updated_at desc, ingested_at desc, raw_id desc
        ) as record_rank
    from {{ source('raw', 'crm_contacts') }}
)

select
    contact_id,
    company_id,
    first_name,
    last_name,
    lower(email) as email,
    split_part(lower(email), '@', 2) as email_domain,
    phone,
    job_title,
    source_updated_at,
    batch_id,
    ingested_at
from ranked
where record_rank = 1
