/**
 * Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: MIT-0
 */

 package com.amazonaws.services.kinesis.samples.dataprocessor;

 import org.springframework.web.bind.annotation.*;
 import org.springframework.http.*;
 
 import java.io.UnsupportedEncodingException;
 import java.nio.ByteBuffer;
 import java.util.*;
 
 import com.amazonaws.services.kinesis.producer.*;
import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.ObjectMapper;
 
 
 @RestController
 public class InputEventController {
 
     //Read Config from env variables
     String region = System.getenv("REGION");
     static String streamName = System.getenv("STREAM_NAME");
 
 
 
     private final KinesisProducerConfiguration config = new KinesisProducerConfiguration().setRegion(region);
     private final KinesisProducer kinesis = new KinesisProducer(config);
 
     //Healthcheck
     @GetMapping(value="/healthcheck")
     public void returnHealthy() {
         //Returns HTTP Status 200 
     }
 
     //Handler for post requests
     @PostMapping(
         value = "/",
         consumes = "!application/x-www-form-urlencoded",
         produces = MediaType.APPLICATION_JSON_VALUE
         )
     public void processInputEvent(@RequestBody Map<String, Object> payload) throws UnsupportedEncodingException {
        //String element = (String) payload.get("data");
        Object element = (Object) payload.get("data");
        //String key = UUID.randomUUID().toString();
        final String key = Long.toString(System.currentTimeMillis());
        // covert element to ByteBuffer
        ObjectMapper mapper = new ObjectMapper();
        try {
                String element_json = mapper.writeValueAsString(element);
                System.out.println("ResultingJSONstring = " + element_json);
                //System.out.println(json);
                ByteBuffer data = ByteBuffer.wrap(element_json.getBytes("UTF-8"));
                kinesis.addUserRecord(streamName, key, data);
            } catch (JsonProcessingException e) {
                e.printStackTrace();
            }
         /*
         * You can implement a synchronous or asynchronous response to results
         * https://docs.aws.amazon.com/streams/latest/dev/kinesis-kpl-writing.html 
         */
 
         return;
     }
     //Handler for post requests with URL encoded input
     @PostMapping(
         value = "/", 
         consumes = "application/x-www-form-urlencoded",
         produces = MediaType.APPLICATION_JSON_VALUE
         )
     public void processInputEventUrlEncoded(@RequestParam Map<String, Object> payload) throws UnsupportedEncodingException {
         //String element = (String) payload.get("data");
         Object element = (Object) payload.get("data");
         //String key = UUID.randomUUID().toString()
         final String key = Long.toString(System.currentTimeMillis());
         // covert element to ByteBuffer
         ObjectMapper mapper = new ObjectMapper();
         try {
                String element_json = mapper.writeValueAsString(element);
                System.out.println("ResultingJSONstring = " + element_json);
                //System.out.println(json);
                ByteBuffer data = ByteBuffer.wrap(element_json.getBytes("UTF-8"));
                kinesis.addUserRecord(streamName, key, data);
            } catch (JsonProcessingException e) {
                e.printStackTrace();
            }
         
         /*
         * You can implement a synchronous or asynchronous response to results
         * https://docs.aws.amazon.com/streams/latest/dev/kinesis-kpl-writing.html 
         */
 
         return;
     }
 } 