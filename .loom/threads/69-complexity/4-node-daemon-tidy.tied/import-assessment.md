# Import-time setup — assessment

Leave item 4 unchanged in this small tidy-up. Import currently constructs and
binds the localhost OSC server on 7770, connects its engine client, builds
`NodeState` (config/UID/assignment/version reads and the enabled-state store
migration), configures logging, registers callbacks and an exit handler, and
constructs the scheduler/generator. The daemon starts their active loops under
`__main__` already. A clean move needs one explicit runtime initializer and a
corresponding ownership/teardown boundary for these shared globals, not merely
moving the server constructor. Eleven living test modules currently import
`bopos`, with several replacing the OSC constructors before import and later
patching the initialized globals. Converting those fixtures while preserving
real startup, callback availability and shutdown ordering would exceed the
cheap-change boundary. `simfleet.py` and `audition.py` import shared protocol
modules, not `bopos`, and none of those imported modules changed here. An import
cleanup would be worthwhile as its own coordinated startup/test-fixture
change; it is not needed to remove the duplication in this stitch. This commit
keeps the module's initialization and exit behavior intact.
