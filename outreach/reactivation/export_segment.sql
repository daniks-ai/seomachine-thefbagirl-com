-- Reactivation segment: registered, never connected Amazon account.
-- Run against readonly prod Postgres (django.poryadok.ru/poryadok, readonly_user;
-- password via PGPASSFILE — never inline).
-- Post-process with the name-cleaning step (see sequence md) before Instantly import.
SELECT u.email,
       u.first_name,
       to_char(u.date_joined,'YYYY-MM-DD') AS joined,
       coalesce(sub.status,'') AS sub_status
FROM auth_user u
JOIN amazon_userprofile up ON up.user_id = u.id
JOIN amazon_amzseller s ON s.id = up.seller_id AND NOT s.is_demo
LEFT JOIN amazon_subscription sub ON sub.user_id = u.id
WHERE u.is_active
  AND u.email <> ''
  -- internal / test accounts. NOTE: is_staff is TRUE for every row in this DB,
  -- so it cannot be used to filter staff out — exclude by address instead.
  AND u.email NOT LIKE '%@daniks.ai'
  AND u.email NOT LIKE '%@daniks.com'
  AND u.email NOT LIKE '%@testing.com'
  AND u.email NOT LIKE 'poryadok.%'
  AND s.ad_api_refresh_token IS NULL          -- never connected Ads API
  AND s.sp_api_refresh_token IS NULL          -- and no SP-API either (any region)
  AND s.sp_api_refresh_token_na IS NULL
  AND s.sp_api_refresh_token_fe IS NULL
  AND coalesce(sub.had_trial, false) = false  -- never activated a trial
  AND up.unsubscribed_announcements_at IS NULL
ORDER BY u.date_joined DESC;
