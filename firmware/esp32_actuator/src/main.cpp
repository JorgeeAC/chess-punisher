#include <Arduino.h>
#include <ArduinoJson.h>
#include <PubSubClient.h>
#include <WiFi.h>

#include "protocol.h"

#ifndef ACTUATOR_LED_PIN
#define ACTUATOR_LED_PIN 2
#endif

#ifndef ACTUATOR_ACTIVE_HIGH
#define ACTUATOR_ACTIVE_HIGH 1
#endif

WiFiClient wifi_client;
PubSubClient mqtt_client(wifi_client);

char cmd_topic[96];
char ack_topic[96];
char status_topic[96];

void set_indicator(bool on) {
#if ACTUATOR_ACTIVE_HIGH
  digitalWrite(ACTUATOR_LED_PIN, on ? HIGH : LOW);
#else
  digitalWrite(ACTUATOR_LED_PIN, on ? LOW : HIGH);
#endif
}

void blink_indicator(unsigned int pulse_ms) {
  set_indicator(true);
  delay(pulse_ms);
  set_indicator(false);
}

void publish_status(bool online, const char *last_command_id) {
  StaticJsonDocument<192> doc;
  doc["online"] = online;
  doc["firmware"] = "0.1.0";
  doc["last_command_id"] = last_command_id;
  doc["rssi"] = WiFi.RSSI();

  char payload[192];
  size_t n = serializeJson(doc, payload, sizeof(payload));
  mqtt_client.publish(status_topic, payload, n, true);
}

void publish_ack(const char *command_id, const char *state, const char *error = "") {
  StaticJsonDocument<192> doc;
  doc["command_id"] = command_id;
  doc["state"] = state;
  doc["ts_ms"] = millis();
  if (strlen(error) > 0) {
    doc["error"] = error;
  }

  char payload[192];
  size_t n = serializeJson(doc, payload, sizeof(payload));
  mqtt_client.publish(ack_topic, payload, n, false);
}

void callback(char *topic, byte *payload, unsigned int length) {
  if (strcmp(topic, cmd_topic) != 0) {
    return;
  }

  StaticJsonDocument<384> doc;
  auto err = deserializeJson(doc, payload, length);
  if (err) {
    publish_ack("unknown", "rejected", "invalid_json");
    return;
  }

  const char *command_id = doc["command_id"] | "";
  if (strlen(command_id) == 0) {
    publish_ack("unknown", "rejected", "missing_command_id");
    return;
  }
  unsigned int pulse_ms = doc["pulse_ms"] | 120;
  if (pulse_ms == 0 || pulse_ms > 2000) {
    pulse_ms = 120;
  }

  Serial.printf("command received: %s\n", command_id);
  publish_ack(command_id, "received");

  // Visual confirmation for bring-up before servo control is wired in.
  blink_indicator(pulse_ms);
  Serial.printf("command executed: %s\n", command_id);
  publish_ack(command_id, "executed");
  publish_status(true, command_id);
}

void ensure_mqtt() {
  while (!mqtt_client.connected()) {
    if (mqtt_client.connect(DEVICE_ID)) {
      mqtt_client.subscribe(cmd_topic, 1);
      Serial.printf("mqtt connected, subscribed to %s\n", cmd_topic);
      publish_status(true, "none");
      break;
    }
    Serial.println("mqtt connect retry");
    delay(500);
  }
}

void setup() {
  Serial.begin(115200);
  pinMode(ACTUATOR_LED_PIN, OUTPUT);
  set_indicator(false);

  snprintf(cmd_topic, sizeof(cmd_topic), COMMAND_TOPIC_TEMPLATE, DEVICE_ID);
  snprintf(ack_topic, sizeof(ack_topic), ACK_TOPIC_TEMPLATE, DEVICE_ID);
  snprintf(status_topic, sizeof(status_topic), STATUS_TOPIC_TEMPLATE, DEVICE_ID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.printf("connecting to wifi ssid=%s\n", WIFI_SSID);
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
  }
  Serial.printf("wifi connected, ip=%s\n", WiFi.localIP().toString().c_str());

  mqtt_client.setServer(MQTT_HOST, MQTT_PORT);
  mqtt_client.setCallback(callback);
}

void loop() {
  ensure_mqtt();
  mqtt_client.loop();
}
