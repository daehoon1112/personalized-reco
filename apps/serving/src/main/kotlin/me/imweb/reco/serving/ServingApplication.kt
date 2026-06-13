package me.imweb.reco.serving

import org.springframework.boot.autoconfigure.SpringBootApplication
import org.springframework.boot.runApplication

@SpringBootApplication
class ServingApplication

fun main(args: Array<String>) {
    runApplication<ServingApplication>(*args)
}
