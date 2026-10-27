select
    md5('order|' || orders.order_id) as order_key,
    orders.order_id,
    customers.customer_key,
    orders.customer_id as erp_customer_id,
    orders.order_date,
    orders.product_line,
    orders.order_status,
    orders.order_amount,
    orders.source_updated_at
from {{ ref('stg_erp_orders') }} as orders
inner join {{ ref('dim_customer') }} as customers
    on orders.customer_id = customers.erp_customer_id
