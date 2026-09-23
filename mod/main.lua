-- Read-only snapshot bridge. Requires Steamodded. Never sends commands to the game.
local filename = "balatro_coach_state.json"
local elapsed = 0

local function escape(value)
    return '"' .. tostring(value):gsub('\\', '\\\\'):gsub('"', '\\"')
        :gsub('\n', '\\n'):gsub('\r', '\\r'):gsub('\t', '\\t') .. '"'
end

local function json(value)
    local kind = type(value)
    if kind == 'nil' then return 'null' end
    if kind == 'string' then return escape(value) end
    if kind == 'boolean' then return tostring(value) end
    if kind == 'number' then
        if value ~= value or value == math.huge or value == -math.huge then return 'null' end
        return tostring(value)
    end
    if kind ~= 'table' then return 'null' end
    local is_array = true
    local count = 0
    for key in pairs(value) do
        count = count + 1
        if type(key) ~= 'number' or key < 1 or key % 1 ~= 0 then is_array = false end
    end
    if is_array then
        for index = 1, count do
            if value[index] == nil then is_array = false; break end
        end
    end
    local parts = {}
    if is_array then
        for index = 1, count do parts[#parts + 1] = json(value[index]) end
        return '[' .. table.concat(parts, ',') .. ']'
    end
    for key, item in pairs(value) do
        parts[#parts + 1] = escape(key) .. ':' .. json(item)
    end
    return '{' .. table.concat(parts, ',') .. '}'
end

local function card_info(card)
    if not card then return nil end
    local center = card.config and card.config.center or {}
    local base = card.base or {}
    return {
        key = center.key or '',
        name = center.name or card.ability and card.ability.name or '',
        set = center.set or '',
        cost = card.cost or 0,
        sell_cost = card.sell_cost or 0,
        kind = center.kind or '',
        choose = center.config and center.config.choose or 0,
        rank = base.value or '',
        suit = base.suit or '',
        edition = card.edition and (card.edition.type or '') or '',
        enhancement = card.ability and card.ability.name or '',
        seal = card.seal or '',
        debuffed = card.debuff or false,
        eternal = card.ability and card.ability.eternal or false,
    }
end

local function area_cards(area)
    local out = {}
    if area and area.cards then
        for _, card in ipairs(area.cards) do
            out[#out + 1] = card_info(card)
        end
    end
    return out
end

local function snapshot()
    if not G or not G.GAME or not G.GAME.round_resets then return nil end
    local game = G.GAME
    local round = game.current_round or {}
    local back = game.selected_back
    local center = back and back.effect and back.effect.center or {}
    local blind = game.blind or {}
    local hands = {}
    for name, value in pairs(game.hands or {}) do
        hands[name] = {
            level = value.level or 1,
            played = value.played or 0,
            visible = value.visible or false,
            chips = value.chips,
            mult = value.mult,
        }
    end
    local vouchers = {}
    for key, used in pairs(game.used_vouchers or {}) do
        if used then vouchers[#vouchers + 1] = key end
    end
    table.sort(vouchers)
    local state_name = tostring(G.STATE or '')
    if G.STATES then
        for name, code in pairs(G.STATES) do
            if code == G.STATE then state_name = name; break end
        end
    end
    return {
        schema = 1,
        saved_at = os.time(),
        stage = state_name,
        deck = center.key or (back and back.name) or 'unknown',
        ante = game.round_resets.ante or 1,
        round = game.round or 0,
        money = game.dollars or 0,
        reroll_cost = round.reroll_cost or 0,
        hands_left = round.hands_left or 0,
        discards_left = round.discards_left or 0,
        blind = {name = blind.name or '', chips = blind.chips or 0},
        chips_scored = game.chips or 0,
        most_played_hand = round.most_played_poker_hand or 'High Card',
        hands = hands,
        vouchers = vouchers,
        jokers = area_cards(G.jokers),
        joker_slots = G.jokers and G.jokers.config and G.jokers.config.card_limit or 0,
        consumables = area_cards(G.consumeables),
        consumable_slots = G.consumeables and G.consumeables.config and G.consumeables.config.card_limit or 0,
        last_tarot_planet = type(game.last_tarot_planet) == 'string' and game.last_tarot_planet or '',
        hand_cards = area_cards(G.hand),
        deck_cards = area_cards(G.deck),
        discard_cards = area_cards(G.discard),
        shop_cards = area_cards(G.shop_jokers),
        shop_vouchers = area_cards(G.shop_vouchers),
        shop_boosters = area_cards(G.shop_booster),
        pack_cards = area_cards(G.pack_cards),
        pack_choices = game.pack_choices or 0,
    }
end

local original_update = Game.update
function Game:update(dt)
    original_update(self, dt)
    elapsed = elapsed + (dt or 0)
    if elapsed < 0.8 then return end
    elapsed = 0
    -- Do not let a snapshot error affect gameplay.
    pcall(function()
        local state = snapshot()
        if not state then return end
        love.filesystem.write(filename, json(state))
    end)
end
