with order_summary as (
    select
        customer_key,
        min(order_date) as first_order_date,
        max(order_date) as last_order_date,
        count(*) as order_count,
        count(*) filter (where order_status = 'Completed') as completed_order_count,
        sum(order_amount) filter (where order_status = 'Completed') as completed_revenue
    from {{ ref('fact_orders') }}
    group by customer_key
)

select
    customers.customer_key,
    customers.erp_customer_id,
    customers.crm_company_id,
    customers.customer_name,
    customers.city,
    customers.state,
    customers.owner_id,
    customers.is_active,
    customers.match_method,
    customers.match_confidence,
    orders.first_order_date,
    orders.last_order_date,
    coalesce(orders.order_count, 0) as order_count,
    coalesce(orders.completed_order_count, 0) as completed_order_count,
    coalesce(orders.completed_revenue, 0) as completed_revenue
from {{ ref('dim_customer') }} as customers
left join order_summary as orders
    on customers.customer_key = orders.customer_key
