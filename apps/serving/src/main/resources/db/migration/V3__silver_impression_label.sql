-- Silver: 라벨링된 impression (1 impression = 1행). 라벨링 배치(#14)가 적재.
-- bronze(events_raw)에서 전량 재생성 가능한 파생 레이어 → is_delete 없음(재빌드로 대체),
-- 레이어 간 물리 FK 없음(논리 참조만).
--
-- attribution v1 규칙 (label_version에 기록):
--   click    = 같은 session_id + 같은 request_id + 같은 item_id의 후행 클릭 귀속
--   purchase = 해당 아이템 click_date(없으면 cart_date)로부터 24h 이내 귀속

CREATE TABLE impression_label (
    id              bigserial    PRIMARY KEY,
    impression_id   varchar(36)  NOT NULL,
    event_date      timestamptz  NOT NULL,
    user_id         varchar(50)  NULL,
    item_id         varchar(50)  NOT NULL,
    session_id      varchar(36)  NULL,
    request_id      varchar(36)  NULL,
    position        int          NULL,
    device          varchar(20)  NULL,
    page            varchar(50)  NULL,
    model_version   varchar(50)  NULL,
    is_click        boolean      NOT NULL DEFAULT false,
    click_date      timestamptz  NULL,
    is_cart         boolean      NOT NULL DEFAULT false,
    cart_date       timestamptz  NULL,
    is_purchase     boolean      NOT NULL DEFAULT false,
    purchase_date   timestamptz  NULL,
    purchase_amount bigint       NULL,
    label           smallint     NOT NULL DEFAULT 0,
    label_version   varchar(100) NOT NULL,
    create_date     timestamptz  NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX ux_impressionlabel_impressionid ON impression_label (impression_id);
CREATE INDEX ix_impressionlabel_userid_eventdate ON impression_label (user_id, event_date);
CREATE INDEX ix_impressionlabel_itemid ON impression_label (item_id);
CREATE INDEX ix_impressionlabel_eventdate ON impression_label (event_date);

COMMENT ON TABLE  impression_label                 IS '실버라벨링된노출(1노출1행)';
COMMENT ON COLUMN impression_label.id              IS '고유식별자';
COMMENT ON COLUMN impression_label.impression_id   IS 'events_raw.event_id논리참조';
COMMENT ON COLUMN impression_label.event_date      IS '노출시각';
COMMENT ON COLUMN impression_label.user_id         IS '유저(비회원NULL)';
COMMENT ON COLUMN impression_label.item_id         IS '아이템';
COMMENT ON COLUMN impression_label.session_id      IS '세션';
COMMENT ON COLUMN impression_label.request_id      IS '노출배치키(context.requestId)';
COMMENT ON COLUMN impression_label.position        IS '노출순위(bias보정용)';
COMMENT ON COLUMN impression_label.device          IS '노출시점디바이스(point-in-time스냅샷)';
COMMENT ON COLUMN impression_label.page            IS '노출시점페이지';
COMMENT ON COLUMN impression_label.model_version   IS '노출시점서빙모델버전';
COMMENT ON COLUMN impression_label.is_click        IS '클릭여부';
COMMENT ON COLUMN impression_label.click_date      IS '클릭시각';
COMMENT ON COLUMN impression_label.is_cart         IS '장바구니여부';
COMMENT ON COLUMN impression_label.cart_date       IS '장바구니시각';
COMMENT ON COLUMN impression_label.is_purchase     IS '구매여부';
COMMENT ON COLUMN impression_label.purchase_date   IS '구매시각';
COMMENT ON COLUMN impression_label.purchase_amount IS '구매금액(KRW정수)';
COMMENT ON COLUMN impression_label.label           IS '최대행동(0=none|1=click|2=cart|3=purchase)';
COMMENT ON COLUMN impression_label.label_version   IS '라벨링규칙버전(귀속윈도값포함)';
COMMENT ON COLUMN impression_label.create_date     IS '생성시각';
