UPDATE vacancy_web
SET (raw_html, status_code, last_check) =
    (SELECT raw_html, status_code, datetime(last_check)
     FROM vacancy_web_backup
     WHERE vacancy_web_backup.url = vacancy_web.url)
WHERE url IN (SELECT url FROM vacancy_web_backup);