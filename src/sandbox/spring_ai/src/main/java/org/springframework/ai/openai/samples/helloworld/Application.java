/*
Copyright (c) 2023, 2024, Oracle and/or its affiliates.
Licensed under the Universal Permissive License v1.0 as shown at http://oss.oracle.com/licenses/upl.
*/

package org.springframework.ai.openai.samples.helloworld;

import org.springframework.ai.embedding.EmbeddingModel; 
import org.springframework.ai.chat.client.ChatClient;
import org.springframework.ai.vectorstore.OracleVectorStore;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.context.annotation.Bean;
import org.springframework.jdbc.core.JdbcTemplate;

@SpringBootApplication
public class Application {

    public static void main(String[] args) {
        SpringApplication.run(Application.class, args);
    }

    @Bean
    OracleVectorStore vectorStore(EmbeddingModel ec, JdbcTemplate t) {
        OracleVectorStore ovs = new OracleVectorStore(t, ec, true);
        return ovs;
    }

}
