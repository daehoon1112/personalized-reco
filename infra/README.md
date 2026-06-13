# infra

로컬 실행용 인프라.

- `docker-compose.yml` — **PostgreSQL 16** + **Kafka (KRaft, 단일 노드)**.
- `postgres/init/01_bronze.sql` — Bronze `events_raw` 초기 테이블 (임시; #5에서 Flyway가 인수).

```
make up     # 기동 (헬시까지 대기)
make down   # 종료
```

> 컨슈머는 Python(`apps/pipelines`, `make consume`)이 `events` 토픽 → `events_raw`로 적재한다.
