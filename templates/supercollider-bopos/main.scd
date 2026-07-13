/* bopOS SuperCollider starter patch.

   One sclang process owns one scsynth server and clones one Synth per output
   element. See README.md for the wire seam and deployment assumptions.
*/
(
~bopos = (
    id: -1,
    master: 1.0,
    auditionMatrix: [1.0, 0.0, 0.0, 1.0],
    params: IdentityDictionary[
        \gain -> 0.7,
        \frequency -> 220.0
    ],
    points: Dictionary.new,
    elements: IdentityDictionary.new,
    cues: Dictionary.new,
    paramDefs: List.new
);

// bopOS delivers run context through the environment at launch; a standalone
// `sclang main.scd` degrades to a useful self-generated context instead.
// The run id is opaque: never parse civil time out of it.
~bopos.enginePort = ("BOPOS_ENGINE_PORT".getenv ? "6661").asInteger;
~bopos.seed = ("BOPOS_SEED".getenv ?? { 1000000.rand.asString }).asInteger;
~bopos.runId = "BOPOS_RUN_ID".getenv ?? {
    "standalone-" ++ ~bopos.seed.asString.padLeft(6, "0")
};
~bopos.patch = "BOPOS_ACTIVEPATCH".getenv ? "standalone";
~bopos.assets = "BOPOS_ASSETS".getenv ? "";
thisThread.randSeed = ~bopos.seed;

// bopos.py (or the audition rig) strips fleet selectors and relays the
// engine surface to this instance's assigned port: identity, patch params,
// master, point scalars, and scheduled cue fires. Production default is
// 6661; audition instances each receive their own BOPOS_ENGINE_PORT, so no
// instance ever attempts a fixed shared bind.
if(thisProcess.openUDPPort(~bopos.enginePort).not) {
    ("bopOS: could not open engine port " ++ ~bopos.enginePort).postln;
};

s.waitForBoot {
    // Wave 1 keeps the patch/monitor ABI fixed at two ordered channels.
    var channels = 2;
    ~bopos.mixBus = Bus.audio(s, channels);

    SynthDef(\boposElement, { |bus=0, gain=0.7, frequency=220, proximity=0|
        var signal = SinOsc.ar(frequency.clip(20, 20000));
        var envelope = Lag.kr(gain.clip(0, 1) * proximity.clip(0, 1), 0.03);
        Out.ar(bus, signal * envelope * 0.15);
    }).add;

    // The bopos.out~ twin: the only final output stage. Audition applies a
    // fixed-stereo matrix before master; both controls are independently
    // smoothed and neither is composed into a patch parameter.
    SynthDef(\boposOut, {
        |bus=0, master=1, l0=1, l1=0, r0=0, r1=1|
        var signal = In.ar(bus, 2);
        var gains = Lag.kr([l0, l1, r0, r1].clip(0, 1), 0.02);
        var auditioned = [
            (signal[0] * gains[0]) + (signal[1] * gains[1]),
            (signal[0] * gains[2]) + (signal[1] * gains[3])
        ];
        Out.ar(0, auditioned * Lag.kr(master.clip(0, 1), 0.03));
    }).add;
    s.sync;

    ~bopos.out = Synth.tail(s, \boposOut, [
        \bus, ~bopos.mixBus.index,
        \master, ~bopos.master,
        \l0, ~bopos.auditionMatrix[0],
        \l1, ~bopos.auditionMatrix[1],
        \r0, ~bopos.auditionMatrix[2],
        \r1, ~bopos.auditionMatrix[3]
    ]);

    ~bopos.ensureElement = { |element|
        var index = element.asInteger;
        if(index >= 0 and: { index < channels } and: {
            ~bopos.elements[index].isNil
        }) {
            ~bopos.elements[index] = Synth.before(~bopos.out, \boposElement, [
                \bus, ~bopos.mixBus.index + index,
                \gain, ~bopos.params[\gain],
                \frequency, ~bopos.params[\frequency]
            ]);
        };
        ~bopos.elements[index]
    };

    ~bopos.setParam = { |name, value|
        var key = name.asSymbol;
        ~bopos.params[key] = value;
        ~bopos.elements.values.do { |synth| synth.set(key, value) };
    };

    ~bopos.installParamRoutes = {
        ~bopos.paramDefs.do { |definition| definition.free };
        ~bopos.paramDefs.clear;
        [\gain, \frequency].do { |name|
            var receive = { |message| ~bopos[\setParam].(name, message[1]) };
            ~bopos.paramDefs.add(OSCdef(
                ("bopos_all_" ++ name).asSymbol,
                receive,
                ("/p/" ++ name).asSymbol,
                recvPort: ~bopos.enginePort
            ));
        };
    };

    OSCdef(\boposIdentity, { |message|
        ~bopos.id = message[1].asInteger;
        ("bopOS device id: " ++ ~bopos.id).postln;
    }, '/id', recvPort: ~bopos.enginePort);

    OSCdef(\boposMaster, { |message|
        ~bopos.master = message[1].asFloat.clip(0, 1);
        ~bopos.out.set(\master, ~bopos.master);
    }, '/os/master', recvPort: ~bopos.enginePort);

    // Private complete-frame audition state. Reject the whole candidate before
    // changing retained state so malformed input cannot mute or partially remap.
    OSCdef(\boposAuditionMatrix, { |message|
        var gains;
        var valid = message.size == 5;
        if(valid) {
            gains = message.copyRange(1, 4);
            valid = gains.every { |value|
                value.isNumber and: { value.isNaN.not } and: {
                    value >= 0 and: { value <= 1 }
                }
            };
        };
        if(valid) {
            ~bopos.auditionMatrix = gains.collect(_.asFloat);
            ~bopos.out.set(
                \l0, ~bopos.auditionMatrix[0],
                \l1, ~bopos.auditionMatrix[1],
                \r0, ~bopos.auditionMatrix[2],
                \r1, ~bopos.auditionMatrix[3]
            );
        };
    }, '/audition/matrix', recvPort: ~bopos.enginePort);

    // The bopos.point twin. State is keyed by [pointId, element]. This starter
    // voice demonstrates point 0 as amplitude; authors can read any key and
    // map it to any synthesis parameter.
    OSCdef(\boposPoint, { |message|
        var point = message[1].asInteger;
        var element = message[2].asInteger;
        var value = message[3].asFloat.clip(0, 1);
        var synth;
        ~bopos.points[[point, element]] = value;
        synth = ~bopos[\ensureElement].(element);
        if(point == 0 and: { synth.notNil }) {
            synth.set(\proximity, value);
        };
    }, '/pt', recvPort: ~bopos.enginePort);

    OSCdef(\boposCue, { |message|
        var cueId = message[1].asString;
        var action = ~bopos.cues[cueId];
        if(action.notNil) { action.value };
        ("bopOS cue: " ++ cueId).postln;
    }, '/cue', recvPort: ~bopos.enginePort);

    OSCdef(\boposNotify, { |message|
        ("bopOS notify: " ++ message[1]).postln;
    }, '/notify', recvPort: ~bopos.enginePort);

    ~bopos[\installParamRoutes].();
    ~bopos.cues["ping"] = {
        ("ping state master=" ++ ~bopos.master
            ++ " gain=" ++ ~bopos.params[\gain]
            ++ " frequency=" ++ ~bopos.params[\frequency]).postln;
    };

    // Retrying /config acquisition: ask the framework for identity every
    // couple of seconds until /id lands. A lost boot-time request is then
    // just one retry away, and standalone runs simply keep the -1 identity.
    ~bopos.configRetry = Routine {
        var framework = NetAddr("127.0.0.1", 7770);
        while { ~bopos.id < 0 } {
            framework.sendMsg('/config');
            2.wait;
        };
    }.play(AppClock);

    ("bopOS SuperCollider template ready — run " ++ ~bopos.runId
        ++ " seed " ++ ~bopos.seed
        ++ " port " ++ ~bopos.enginePort).postln;
};
)
