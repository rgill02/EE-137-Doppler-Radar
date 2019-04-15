const unsigned long TS_US = 200;
const unsigned short MAX_BUF_SIZE = 2501; //2500 samples plus 1 sync
const unsigned short BUF_LEN_BYTES = MAX_BUF_SIZE * sizeof(unsigned short);
const unsigned char SAMPLE_PIN = 3;

unsigned long cur_time;  //Will overflow after 1.2 hours
unsigned long prev_time = 0;
unsigned short cur_idx = 1;
unsigned short buf[MAX_BUF_SIZE];

void setup()
{
  Serial.begin(115200);
  buf[0] = (unsigned short) -1; //sync
}

void loop()
{
  cur_time = micros();
  if ((cur_time - prev_time) >= TS_US) {
    buf[cur_idx] = analogRead(SAMPLE_PIN);
    cur_idx++;
    if (cur_idx >= MAX_BUF_SIZE) {
      Serial.write((byte *) buf, BUF_LEN_BYTES);
      cur_idx = 1;
      buf[0] = (unsigned short) -1; //sync
    }
    prev_time = cur_time;
  }
}
