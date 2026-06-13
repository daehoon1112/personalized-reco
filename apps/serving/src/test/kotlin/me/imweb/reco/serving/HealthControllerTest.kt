package me.imweb.reco.serving

import io.kotest.core.spec.style.StringSpec
import io.kotest.matchers.shouldBe
import me.imweb.reco.serving.api.HealthController

/** 단위 테스트 — 순수 로직, I/O 없음. */
class HealthControllerTest : StringSpec({
    "health 는 UP 을 반환한다" {
        HealthController().health() shouldBe mapOf("status" to "UP")
    }
})
