#include "esp_camera.h" 
#include <WiFi.h> 
#include "esp_timer.h" 
#include "img_converters.h" 
#include "Arduino.h" 
#include "fb_gfx.h" 
#include "soc/soc.h"  
#include "soc/rtc_cntl_reg.h"  
#include "esp_http_server.h" 
 
// ======================= 
// WiFi Credentials - **MUST BE 2.4 GHz NETWORK** 
// ======================= 
const char* ssid = "”; 
const char* password = "”; 
 
// ======================= 
// Camera Configuration (AI Thinker Model) 
// ======================= 
#define CAMERA_MODEL_AI_THINKER 
#define PWDN_GPIO_NUM 32 
#define RESET_GPIO_NUM -1 
#define XCLK_GPIO_NUM 0 
#define SIOD_GPIO_NUM 26 
#define SIOC_GPIO_NUM 27 
#define Y9_GPIO_NUM 35 
#define Y8_GPIO_NUM 34 
#define Y7_GPIO_NUM 39 
#define Y6_GPIO_NUM 36 
#define Y5_GPIO_NUM 21 
#define Y4_GPIO_NUM 19 
#define Y3_GPIO_NUM 18 
#define Y2_GPIO_NUM 5 
#define VSYNC_GPIO_NUM 25 
#define HREF_GPIO_NUM 23 
#define PCLK_GPIO_NUM 22 
 
httpd_handle_t snapshot_httpd = NULL; 
 
// --- REVISED SNAPSHOT HANDLER FOR RELIABILITY --- 
static esp_err_t snapshot_handler(httpd_req_t *req){ 
camera_fb_t * fb = NULL; 
esp_err_t res = ESP_OK; 
// 1. Get the camera frame buffer 
fb = esp_camera_fb_get(); 
if (!fb) { 
Serial.println("Camera capture failed"); 
httpd_resp_send_500(req); 
return ESP_FAIL; 
} 
 
// 2. Set the content type 
res = httpd_resp_set_type(req, "image/jpeg"); 
if(res != ESP_OK){ 
esp_camera_fb_return(fb); 
return res; 
} 
 
// 3. Set the content length (MANDATORY for single shot) 
char len_buf[16]; 
snprintf(len_buf, 16, "%u", fb->len); 
httpd_resp_set_hdr(req, "Content-Length", len_buf); 
 
// 4. Send the JPEG data (using chunking for robustness) 
res = httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len); 
// 5. Signal end of response 
if(res == ESP_OK){ 
res = httpd_resp_send_chunk(req, "", 0); // Send final zero-length chunk 
} 
 
// 6. Return the frame buffer 
esp_camera_fb_return(fb); 
return res; 
} 
// -------------------------------------------------- 
 
void startCameraServer(){ 
httpd_config_t config = HTTPD_DEFAULT_CONFIG(); 
config.server_port = 80; 
 
httpd_uri_t index_uri = { 
.uri = "/", 
.method = HTTP_GET, 
.handler = snapshot_handler,  
.user_ctx = NULL 
}; 
Serial.printf("Starting web server on port: '%d'\n", config.server_port); 
if (httpd_start(&snapshot_httpd, &config) == ESP_OK) { 
httpd_register_uri_handler(snapshot_httpd, &index_uri); 
Serial.println("Snapshot server started."); 
} else { 
Serial.println("Error starting snapshot server!"); 
} 
} 
 
void setup() { 
WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0); //disable brownout detector 
Serial.begin(115200); 
Serial.setDebugOutput(false); 
// --- CAMERA CONFIGURATION --- 
camera_config_t config; 
config.ledc_channel = LEDC_CHANNEL_0; 
config.ledc_timer = LEDC_TIMER_0; 
config.pin_d0 = Y2_GPIO_NUM; 
config.pin_d1 = Y3_GPIO_NUM; 
config.pin_d2 = Y4_GPIO_NUM; 
config.pin_d3 = Y5_GPIO_NUM; 
config.pin_d4 = Y6_GPIO_NUM; 
config.pin_d5 = Y7_GPIO_NUM; 
config.pin_d6 = Y8_GPIO_NUM; 
config.pin_d7 = Y9_GPIO_NUM; 
config.pin_xclk = XCLK_GPIO_NUM; 
config.pin_pclk = PCLK_GPIO_NUM; 
config.pin_vsync = VSYNC_GPIO_NUM; 
config.pin_href = HREF_GPIO_NUM; 
config.pin_sccb_sda = SIOD_GPIO_NUM; 
config.pin_sccb_scl = SIOC_GPIO_NUM; 
config.pin_pwdn = PWDN_GPIO_NUM; 
config.pin_reset = RESET_GPIO_NUM; 
config.xclk_freq_hz = 20000000; 
config.pixel_format = PIXFORMAT_JPEG;  
// Frame size and quality settings 
if(psramFound()){ 
config.frame_size = FRAMESIZE_SVGA; // 800x600 is usually good for scanning 
config.jpeg_quality = 10; 
config.fb_count = 2; 
} else { 
config.frame_size = FRAMESIZE_VGA; // 640x480 without PSRAM 
config.jpeg_quality = 12; 
config.fb_count = 1; 
} 
// Init Camera 
esp_err_t err = esp_camera_init(&config); 
if (err != ESP_OK) { 
Serial.printf("Camera init failed with error 0x%x\n", err); 
return; 
} 
Serial.println("Camera initialized successfully."); 
 
// --- Wi-Fi connection --- 
WiFi.begin(ssid, password); 
Serial.print("Connecting to WiFi"); 
while (WiFi.status() != WL_CONNECTED) { 
delay(500); 
Serial.print("."); 
} 
Serial.println(""); 
Serial.println("WiFi connected"); 
Serial.print("Camera Snapshot Ready! Access at: http://"); 
Serial.print(WiFi.localIP()); 
Serial.println("/"); 
// Start the snapshot web server 
startCameraServer(); 
} 
 
void loop() { 
// Nothing needed in the loop for a simple web server 
delay(10); 
} 
 
