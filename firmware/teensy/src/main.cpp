// Milestone: single-bus, single-controller CAN listener.
//
// Purpose:
//   Prove the physical CAN link to exactly one MKS ODrive Mini works before any
//   command is ever transmitted to it. Context: docs/ARCHITECTURE.md §3-4.
//
// Behavior:
//   Listens on one CAN bus and prints every received frame (raw ID, decoded
//   node/cmd id, raw data bytes) to USB serial. Never transmits anything.
//
// Assumptions (unverified -- see docs/ARCHITECTURE.md §9 Open Questions):
//   - CAN bitrate is the ODrive stock default, 250 kbit/s (kBaudRate below).
//   - The standard-ID bit layout [node_id:6][cmd_id:5] used by stock ODrive
//     CANSimple still holds on this firmware fork. This should be safe to
//     assume even though the fork isn't fully diffed against upstream, since
//     the fork's changes are described as being to payload content (encoder
//     position piggybacked on Heartbeat, a new Iq message), not to address
//     assignment.
//   - No assumption is made about *which* node ID is present -- every frame
//     that arrives is printed, so the actual node ID(s) on the bus can be
//     read directly off the serial monitor.
//
// Limitations:
//   - Exercises one bus only (CAN1 below). Change CAN1 -> CAN2/CAN3 to test
//     a controller on a different bus; this program intentionally does not
//     handle multiple buses at once (see next milestone).
//   - Does not decode Heartbeat payload fields (Axis_Error/Axis_State/etc.)
//     because the fork is documented as having modified that payload layout
//     and that hasn't been confirmed yet. Raw bytes are printed instead so a
//     human can compare them against the fork's source.
//
// Failure modes:
//   - No frames ever printed: rank likely causes in this order -- (1) ODrive
//     not powered, (2) CAN_H/CAN_L swapped or unconnected, (3) missing/wrong
//     bus termination, (4) baud rate mismatch (kBaudRate below vs. the
//     ODrive's actual config), (5) this ODrive's CAN interface not enabled
//     in its config.

#include <FlexCAN_T4.h>

// Which physical bus this build listens on. Per docs/ARCHITECTURE.md §4:
// CAN1 -> Arm 1, CAN2 -> Arm 2, CAN3 -> torso gimbal.
using CanBus = FlexCAN_T4<CAN1, RX_SIZE_256, TX_SIZE_16>;
static const char *kBusName = "CAN1";

CanBus can_bus;

// ODrive stock default CAN bitrate. If no frames ever arrive, this is one of
// the first things to check against the ODrive's real per-axis config.
static constexpr uint32_t kBaudRate = 250000;

void setup() {
  Serial.begin(115200);
  uint32_t serial_wait_start = millis();
  while (!Serial && millis() - serial_wait_start < 3000) {
    // Give the USB serial monitor a few seconds to attach.
  }

  can_bus.begin();
  can_bus.setBaudRate(kBaudRate);

  Serial.println("=== Single-controller CAN listener ===");
  Serial.print("Bus: ");
  Serial.println(kBusName);
  Serial.print("Baud: ");
  Serial.println(kBaudRate);
  Serial.println("Receive-only -- this program never transmits.");
}

void loop() {
  CAN_message_t msg;
  if (!can_bus.read(msg)) {
    return;
  }

  const uint8_t node_id = msg.id >> 5;
  const uint8_t cmd_id = msg.id & 0x1F;

  Serial.print(millis());
  Serial.print(" ms | id=0x");
  Serial.print(msg.id, HEX);
  Serial.print(" node=");
  Serial.print(node_id);
  Serial.print(" cmd=0x");
  Serial.print(cmd_id, HEX);
  Serial.print(" len=");
  Serial.print(msg.len);
  Serial.print(" data=");
  for (uint8_t i = 0; i < msg.len; i++) {
    if (msg.buf[i] < 0x10) {
      Serial.print('0');
    }
    Serial.print(msg.buf[i], HEX);
    Serial.print(' ');
  }
  Serial.println();
}
