-- Headless smoke test: mash A / Start through the title and intro, screenshot every 400 frames.
local out = os.getenv("ZT_OUT")
local frames = 4800
for f = 1, frames do
  local k = {}
  local phase = f % 50
  if phase < 4 then
    if f > 700 and f < 1100 and (f % 200) < 4 then k["Start"] = true else k["A"] = true end
  end
  joypad.set(k)
  emu.frameadvance()
  if f % 400 == 0 then client.screenshot(out .. string.format("_%05d.png", f)) end
end
client.exit()
