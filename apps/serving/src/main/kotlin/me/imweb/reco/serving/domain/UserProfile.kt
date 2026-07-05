package me.imweb.reco.serving.domain

import java.time.Instant

/**
 * 유저 프로필 (`user_profile`, V2 — "user"는 PG 예약어). 비즈니스 키 = [userId] (ux_userprofile_userid).
 */
data class UserProfile(
    val id: Long? = null,
    val userId: String,
    val gender: String? = null,      // F | M
    val birthYear: Int? = null,
    val joinDate: Instant? = null,
    val isConsent: Boolean = false,  // 추적 동의 — false면 개인화 피처 사용 금지
    val attrs: Map<String, Any?> = emptyMap(),
    val isDelete: Boolean = false,
    val createDate: Instant? = null,
    val updateDate: Instant? = null,
    val deleteDate: Instant? = null,
)
