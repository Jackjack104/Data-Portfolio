select
    date_trunc('month', orders.order_date)::date as order_month,
    customers.state,
    customers.owner_id,
    orders.product_line,
    count(*) as order_count,
    count(*) filter (where orders.order_status = 'Completed') as completed_order_count,
    count(*) filter (where orders.order_status = 'Cancelled') as cancelled_order_count,
    count(distinct orders.customer_key) as active_customers,
    sum(orders.order_amount) as gross_order_value,
    sum(orders.order_amount) filter (
        where orders.order_status = 'Completed'
    ) as completed_revenue,
    avg(orders.order_amount) as average_order_value
from {{ ref('fact_orders') }} as orders
inner join {{ ref('dim_customer') }} as customers
    on orders.customer_key = customers.customer_key
group by 1, 2, 3, 4
