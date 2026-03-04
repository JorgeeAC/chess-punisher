#include <Arduino.h>
#include <ArduinoJson.h>
#include <PubSubClient.h>
#include <WiFi.h>

#include "protocol.h"

WiFiClient wifi_client;
PubSubClient mqtt_client(wifi_client);

char cmd_topic[96];
char ack_topic[96];
char status_topic[96];

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

  publish_ack(command_id, "received");

  // TODO: drive servo here based on action/pulse_ms.
  delay(80);
  publish_ack(command_id, "executed");
  publish_status(true, command_id);
}

void ensure_mqtt() {
  while (!mqtt_client.connected()) {
    if (mqtt_client.connect(DEVICE_ID)) {
      mqtt_client.subscribe(cmd_topic, 1);
      publish_status(true, "none");
      break;
    }
    delay(500);
  }
}

void setup() {
  Serial.begin(115200);

  snprintf(cmd_topic, sizeof(cmd_topic), COMMAND_TOPIC_TEMPLATE, DEVICE_ID);
  snprintf(ack_topic, sizeof(ack_topic), ACK_TOPIC_TEMPLATE, DEVICE_ID);
  snprintf(status_topic, sizeof(status_topic), STATUS_TOPIC_TEMPLATE, DEVICE_ID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
  }

  mqtt_client.setServer(MQTT_HOST, MQTT_PORT);
  mqtt_client.setCallback(callback);
}

void loop() {
  ensure_mqtt();
  mqtt_client.loop();
}
