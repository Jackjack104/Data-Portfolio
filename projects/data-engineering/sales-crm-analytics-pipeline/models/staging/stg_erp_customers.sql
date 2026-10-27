with ranked as (
    select
        *,
        row_number() over (
            partition by customer_id
            order by source_updated_at desc, ingested_at desc, raw_id desc
        ) as record_rank
    from {{ source('raw', 'erp_customers') }}
)

select
    customer_id,
    company_name,
    {{ normalize_company_name('company_name') }} as normalized_company_name,
    {{ normalize_domain('email_domain') }} as normalized_domain,
    address,
    city,
    upper(state) as state,
    postal_code,
    is_active,
    source_updated_at,
    batch_id,
    ingested_at
from ranked
where record_rank = 1
