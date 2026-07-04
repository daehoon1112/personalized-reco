-- 메타데이터: 아이템/유저 마스터 (Item·User Feature의 원천).
-- 컨벤션: 셀러업 DB 가이드 + Postgres 적응 (docs/data-model.md 참조).
-- "user"는 PG 예약어라 user_profile 사용.

CREATE TABLE item (
    id          bigserial    PRIMARY KEY,
    item_id     varchar(50)  NOT NULL,
    name        varchar(200) NULL,
    category    varchar(50)  NULL,
    brand       varchar(100) NULL,
    price       bigint       NULL,
    currency    varchar(3)   NOT NULL DEFAULT 'KRW',
    status_cd   varchar(20)  NOT NULL DEFAULT 'sale',
    description varchar      NULL,
    attrs       jsonb        NOT NULL DEFAULT '{}',
    is_delete   boolean      NOT NULL DEFAULT false,
    create_date timestamptz  NOT NULL DEFAULT now(),
    update_date timestamptz  NULL     DEFAULT now(),
    delete_date timestamptz  NULL
);

CREATE UNIQUE INDEX ux_item_itemid ON item (item_id);
CREATE INDEX ix_item_category ON item (category);
CREATE INDEX ix_item_statuscd ON item (status_cd);

COMMENT ON TABLE  item             IS '아이템마스터';
COMMENT ON COLUMN item.id          IS '고유식별자';
COMMENT ON COLUMN item.item_id     IS '비즈니스키(이벤트itemId)';
COMMENT ON COLUMN item.name        IS '상품명';
COMMENT ON COLUMN item.category    IS '카테고리';
COMMENT ON COLUMN item.brand       IS '브랜드';
COMMENT ON COLUMN item.price       IS '가격(KRW정수)';
COMMENT ON COLUMN item.currency    IS '통화';
COMMENT ON COLUMN item.status_cd   IS '상태(sale|soldout|hidden)';
COMMENT ON COLUMN item.description IS '상품설명';
COMMENT ON COLUMN item.attrs       IS '확장속성(임베딩소스·이미지URL등)';
COMMENT ON COLUMN item.is_delete   IS '삭제여부';
COMMENT ON COLUMN item.create_date IS '생성시각';
COMMENT ON COLUMN item.update_date IS '수정시각';
COMMENT ON COLUMN item.delete_date IS '삭제시각';

CREATE TABLE user_profile (
    id          bigserial   PRIMARY KEY,
    user_id     varchar(50) NOT NULL,
    gender      varchar(1)  NULL,
    birth_year  int         NULL,
    join_date   timestamptz NULL,
    is_consent  boolean     NOT NULL DEFAULT false,
    attrs       jsonb       NOT NULL DEFAULT '{}',
    is_delete   boolean     NOT NULL DEFAULT false,
    create_date timestamptz NOT NULL DEFAULT now(),
    update_date timestamptz NULL     DEFAULT now(),
    delete_date timestamptz NULL
);

CREATE UNIQUE INDEX ux_userprofile_userid ON user_profile (user_id);

COMMENT ON TABLE  user_profile             IS '유저프로필';
COMMENT ON COLUMN user_profile.id          IS '고유식별자';
COMMENT ON COLUMN user_profile.user_id     IS '비즈니스키(이벤트userId)';
COMMENT ON COLUMN user_profile.gender      IS '성별(F|M)';
COMMENT ON COLUMN user_profile.birth_year  IS '출생연도';
COMMENT ON COLUMN user_profile.join_date   IS '가입시각';
COMMENT ON COLUMN user_profile.is_consent  IS '추적동의여부';
COMMENT ON COLUMN user_profile.attrs       IS '확장속성';
COMMENT ON COLUMN user_profile.is_delete   IS '삭제여부';
COMMENT ON COLUMN user_profile.create_date IS '생성시각';
COMMENT ON COLUMN user_profile.update_date IS '수정시각';
COMMENT ON COLUMN user_profile.delete_date IS '삭제시각';
