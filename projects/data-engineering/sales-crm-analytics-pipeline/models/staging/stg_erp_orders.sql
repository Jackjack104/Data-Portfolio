with ranked as (
    select
        *,
        row_number() over (
            partition by order_id
            order by source_updated_at desc, ingested_at desc, raw_id desc
        ) as record_rank
    from {{ source('raw', 'erp_orders') }}
)

select
    order_id,
    customer_id,
    order_date,
    product_line,
    order_status,
    order_amount,
    source_updated_at,
    batch_id,
    ingested_at
from ranked
where record_rank = 1
