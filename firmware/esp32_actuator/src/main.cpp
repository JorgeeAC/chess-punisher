#include <Arduino.h>
#include <ArduinoJson.h>
#include <WebServer.h>
#include <WiFi.h>

#ifndef ACTUATOR_LED_PIN
#define ACTUATOR_LED_PIN 2
#endif

#ifndef ACTUATOR_ACTIVE_HIGH
#define ACTUATOR_ACTIVE_HIGH 1
#endif

WebServer server(80);

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

void send_json(int status_code, JsonDocument &doc) {
  char payload[320];
  serializeJson(doc, payload, sizeof(payload));
  server.send(status_code, "application/json", payload);
}

int read_pulse_ms() {
  if (!server.hasArg("pulse_ms")) {
    return 150;
  }
  int pulse_ms = server.arg("pulse_ms").toInt();
  if (pulse_ms < 20 || pulse_ms > 2000) {
    return 150;
  }
  return pulse_ms;
}

void handle_health() {
  StaticJsonDocument<192> doc;
  doc["ok"] = true;
  doc["device_id"] = DEVICE_ID;
  doc["ip"] = WiFi.localIP().toString();
  doc["rssi"] = WiFi.RSSI();
  send_json(200, doc);
}

void handle_root() {
  StaticJsonDocument<224> doc;
  doc["ok"] = true;
  doc["device_id"] = DEVICE_ID;
  doc["health"] = "/health";
  doc["punish"] = "/punish";
  doc["ping"] = "/ping";
  send_json(200, doc);
}

void handle_ping() {
  StaticJsonDocument<128> doc;
  doc["ok"] = true;
  doc["pong"] = true;
  doc["device_id"] = DEVICE_ID;
  send_json(200, doc);
}

void handle_punish() {
  String severity = server.hasArg("severity") ? server.arg("severity") : "TEST";
  String move = server.hasArg("move") ? server.arg("move") : "";
  String loss = server.hasArg("loss") ? server.arg("loss") : "0";
  int pulse_ms = read_pulse_ms();

  Serial.printf(
      "punish severity=%s move=%s loss=%s pulse_ms=%d\n",
      severity.c_str(),
      move.c_str(),
      loss.c_str(),
      pulse_ms);
  blink_indicator(pulse_ms);

  StaticJsonDocument<224> doc;
  doc["ok"] = true;
  doc["device_id"] = DEVICE_ID;
  doc["severity"] = severity;
  doc["move"] = move;
  doc["loss"] = loss;
  doc["pulse_ms"] = pulse_ms;
  send_json(200, doc);
}

void handle_not_found() {
  StaticJsonDocument<160> doc;
  doc["ok"] = false;
  doc["error"] = "not_found";
  doc["path"] = server.uri();
  send_json(404, doc);
}

void setup() {
  Serial.begin(115200);
  pinMode(ACTUATOR_LED_PIN, OUTPUT);
  set_indicator(false);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASS);
  Serial.printf("connecting to wifi ssid=%s\n", WIFI_SSID);
  while (WiFi.status() != WL_CONNECTED) {
    delay(300);
  }
  Serial.printf("wifi connected, ip=%s\n", WiFi.localIP().toString().c_str());
  server.on("/", HTTP_GET, handle_root);
  server.on("/health", HTTP_GET, handle_health);
  server.on("/ping", HTTP_GET, handle_ping);
  server.on("/punish", HTTP_GET, handle_punish);
  server.onNotFound(handle_not_found);
  server.begin();
  Serial.printf("http ready: http://%s/health\n", WiFi.localIP().toString().c_str());
}

void loop() {
  server.handleClient();
}
