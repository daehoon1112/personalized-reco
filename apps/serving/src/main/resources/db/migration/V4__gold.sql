-- Gold: 모델별 학습/서빙 입력. 배치가 적재하며 silver에서 전량 재생성 가능(파생 레이어 → is_delete 없음).
--   item_popularity        인기순(MVP) 입력 — 배치(#10)
--   user_item_interaction  CF(implicit/LightFM) 희소행렬 입력
--   recommendation         배치 사전계산 결과 = 추천 API(#8)가 읽는 서빙 테이블

CREATE TABLE item_popularity (
    id               bigserial     PRIMARY KEY,
    base_date        date          NOT NULL,
    window_days      smallint      NOT NULL,
    item_id          varchar(50)   NOT NULL,
    impression_count bigint        NOT NULL DEFAULT 0,
    click_count      bigint        NOT NULL DEFAULT 0,
    cart_count       bigint        NOT NULL DEFAULT 0,
    purchase_count   bigint        NOT NULL DEFAULT 0,
    buyer_count      bigint        NOT NULL DEFAULT 0,
    score            numeric(12,6) NOT NULL,
    create_date      timestamptz   NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX ux_itempopularity_basedate_windowdays_itemid
    ON item_popularity (base_date, window_days, item_id);

COMMENT ON TABLE  item_popularity                  IS '골드인기순집계(윈도별)';
COMMENT ON COLUMN item_popularity.id               IS '고유식별자';
COMMENT ON COLUMN item_popularity.base_date        IS '집계기준일';
COMMENT ON COLUMN item_popularity.window_days      IS '집계윈도일수(7|30)';
COMMENT ON COLUMN item_popularity.item_id          IS '아이템';
COMMENT ON COLUMN item_popularity.impression_count IS '노출수';
COMMENT ON COLUMN item_popularity.click_count      IS '클릭수';
COMMENT ON COLUMN item_popularity.cart_count       IS '장바구니수';
COMMENT ON COLUMN item_popularity.purchase_count   IS '구매수';
COMMENT ON COLUMN item_popularity.buyer_count      IS '중복제거구매자수';
COMMENT ON COLUMN item_popularity.score            IS '인기점수(행동가중합+시간감쇠)';
COMMENT ON COLUMN item_popularity.create_date      IS '생성시각';

CREATE TABLE user_item_interaction (
    id               bigserial     PRIMARY KEY,
    user_id          varchar(50)   NOT NULL,
    item_id          varchar(50)   NOT NULL,
    impression_count int           NOT NULL DEFAULT 0,
    click_count      int           NOT NULL DEFAULT 0,
    cart_count       int           NOT NULL DEFAULT 0,
    purchase_count   int           NOT NULL DEFAULT 0,
    weight           numeric(12,4) NOT NULL,
    last_event_date  timestamptz   NOT NULL,
    create_date      timestamptz   NOT NULL DEFAULT now(),
    update_date      timestamptz   NULL DEFAULT now()
);

CREATE UNIQUE INDEX ux_useriteminteraction_userid_itemid
    ON user_item_interaction (user_id, item_id);

COMMENT ON TABLE  user_item_interaction                  IS '골드유저아이템상호작용(CF희소행렬입력)';
COMMENT ON COLUMN user_item_interaction.id               IS '고유식별자';
COMMENT ON COLUMN user_item_interaction.user_id          IS '유저';
COMMENT ON COLUMN user_item_interaction.item_id          IS '아이템';
COMMENT ON COLUMN user_item_interaction.impression_count IS '노출수';
COMMENT ON COLUMN user_item_interaction.click_count      IS '클릭수';
COMMENT ON COLUMN user_item_interaction.cart_count       IS '장바구니수';
COMMENT ON COLUMN user_item_interaction.purchase_count   IS '구매수';
COMMENT ON COLUMN user_item_interaction.weight           IS '암묵피드백가중합(EVENT_WEIGHTS)';
COMMENT ON COLUMN user_item_interaction.last_event_date  IS '최종행동시각';
COMMENT ON COLUMN user_item_interaction.create_date      IS '생성시각';
COMMENT ON COLUMN user_item_interaction.update_date      IS '수정시각';

CREATE TABLE recommendation (
    id            bigserial     PRIMARY KEY,
    user_id       varchar(50)   NOT NULL,
    rank          smallint      NOT NULL,
    item_id       varchar(50)   NOT NULL,
    score         numeric(12,6) NOT NULL,
    strategy      varchar(20)   NOT NULL,
    model_version varchar(50)   NOT NULL,
    compute_date  timestamptz   NOT NULL,
    create_date   timestamptz   NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX ux_recommendation_userid_rank ON recommendation (user_id, rank);

COMMENT ON TABLE  recommendation               IS '배치사전계산추천결과(서빙조회테이블)';
COMMENT ON COLUMN recommendation.id            IS '고유식별자';
COMMENT ON COLUMN recommendation.user_id       IS '유저(콜드스타트전역폴백은_global센티널)';
COMMENT ON COLUMN recommendation.rank          IS '추천순위(1-base)';
COMMENT ON COLUMN recommendation.item_id       IS '아이템';
COMMENT ON COLUMN recommendation.score         IS '추천점수';
COMMENT ON COLUMN recommendation.strategy      IS '전략(popularity|cf)';
COMMENT ON COLUMN recommendation.model_version IS '모델버전';
COMMENT ON COLUMN recommendation.compute_date  IS '계산시각';
COMMENT ON COLUMN recommendation.create_date   IS '생성시각';
