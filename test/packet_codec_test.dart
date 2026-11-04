import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:blousab/services/packet_codec.dart';

void main() {
  final big = jsonEncode({'type': 'chat', 'text': 'مرحبا ' * 400});

  test('small packets pass through untouched', () {
    const small = '{"type":"ack","id":"1"}';
    expect(PacketCodec.pack(small), small);
    expect(PacketCodec.unpack(small), small);
  });

  test('large packets are compressed and restored exactly', () {
    final packed = PacketCodec.pack(big);
    expect(packed.length, lessThan(big.length));
    expect(packed.startsWith('{"type":"z"'), isTrue);
    expect(packed.contains('\n'), isFalse); // single line for Bluetooth framing
    expect(PacketCodec.unpack(packed), big);
  });

  test('incompressible data is left as it is', () {
    final noise = jsonEncode({'d': base64Encode(List<int>.generate(900, (i) => (i * 7919 + i * i) % 251))});
    expect(PacketCodec.unpack(PacketCodec.pack(noise)), noise);
  });

  test('corrupt or lying packets are dropped', () {
    expect(PacketCodec.unpack('{"type":"z","enc":"gzip+b64","raw":5,"d":"AAAA"}'), '');
    final packed = jsonDecode(PacketCodec.pack(big)) as Map<String, dynamic>;
    packed['raw'] = 10; // declared size smaller than the real one
    expect(PacketCodec.unpack(jsonEncode(packed)), '');
  });

  test('inflate refuses output above the limit', () {
    final zeros = PacketCodec.deflate(List<int>.filled(200000, 0));
    expect(PacketCodec.inflate(zeros, maxBytes: 1000), isNull);
    expect(PacketCodec.inflate(zeros, maxBytes: 300000)?.length, 200000);
  });

  test('stored data round-trips and old plain data is still readable', () {
    expect(StorageCodec.unpack(StorageCodec.pack(big)), big);
    expect(StorageCodec.unpack('[1,2,3]'), '[1,2,3]');
    expect(StorageCodec.pack('short'), 'short');
  });
}
