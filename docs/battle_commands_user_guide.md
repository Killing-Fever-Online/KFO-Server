# Battle Commands — User Guide

A practical guide to fighters, moves, items, battles, guilds, and GM administration.

Based on the current battle command implementation and the item-enabled battle system.

*September 22, 2026*

---

## Table of Contents

1. [Before You Start](#1-before-you-start)
2. [Fighter Management](#2-fighter-management)
3. [Creating and Managing Moves](#3-creating-and-managing-moves)
4. [Items and the Battle Bag](#4-items-and-the-battle-bag)
5. [Item Definitions and Value Rules](#5-item-definitions-and-value-rules)
6. [Joining and Playing a Battle](#6-joining-and-playing-a-battle)
7. [Battle Effects Reference](#7-battle-effects-reference)
8. [Item Effect List](#8-item-effect-list)
9. [Guilds](#9-guilds)
10. [GM and Battle Administration](#10-gm-and-battle-administration)
11. [Practical Example: Using an Item in a Round](#11-practical-example-using-an-item-in-a-round)
12. [Common Troubleshooting](#12-common-troubleshooting)
13. [Command Cheat Sheet](#13-command-cheat-sheet)

---

## 1. Before You Start

All commands shown in this guide use the server command prefix `/`. Replace placeholders such as `FighterName`, `ItemName`, or `Target_ID` with actual values.

**GM** means the command is restricted to the configured hub owners / game masters.

**Client IDs** are the numeric IDs displayed by battle information and guild information. They are used when a command asks for `Target_ID`.

**Names** are generally normalized to lowercase by the implementation. For move lookup, use either the move name or its numeric ID shown by `/info_fighter`.

### Quick start

1. Choose a fighter with `/choose_fighter <NameFighter>`.
2. Check the fighter with `/info_fighter` and note the move IDs and your item bag.
3. Enter the battle with `/fight`.
4. During each turn, choose a move with `/use_move <MoveName-or-ID> <Target_ID>`, use an item with `/use_item <ItemName> <Target_ID>`, or use `/skip_move`.
5. Use `/battle_info` to see the current participants and, when enabled, their HP percentages.

### Important item note

Items are stored separately from moves. Your battle bag contains item copies, and an item is consumed when the selected item action is actually resolved. A failed selection does not consume the item.

---

## 2. Fighter Management

### `/choose_fighter`

Choose a fighter from the server list and immediately display its stats and moves.

**Example**
```text
/choose_fighter Knight
```

### `/info_fighter`

Display the currently selected fighter, its current battle status, HP, mana, combat stats, all available moves, and the owner's current item bag.

**Example**
```text
/info_fighter
```

### `/create_fighter` (GM)

Create a new fighter definition. HP must be greater than zero; the other base values must be zero or greater. New fighters start with no moves.

**Example**
```text
/create_fighter Knight 100 50 20 15 10 12 18
```

### `/modify_stat` (GM)

Change one fighter base stat. Accepted stat names are `HP`, `MANA`, `ATK`, `DEF`, `SPA`, `SPD`, and `SPE`. Values cannot be negative.

**Example**
```text
/modify_stat Knight hp 120
```

### `/delete_fighter` (GM)

Delete the fighter YAML definition from server storage.

**Example**
```text
/delete_fighter Knight
```

### Fighter stat reference

| Stat | Meaning |
|------|---------|
| HP | Health. Reaching 0 removes the fighter from the active battle. |
| MANA | Resource consumed when a move is selected. |
| ATK | Physical attack stat used by ATK moves. |
| DEF | Physical defense stat used to mitigate ATK damage. |
| SPA | Special attack stat used by SPA moves. |
| SPD | Special defense stat used to mitigate SPA damage. |
| SPE | Speed. Fighters act in descending speed order. |

---

## 3. Creating and Managing Moves

### `/create_move`

Add a move to the currently selected fighter. The move type must be `atk` or `spa`. Mana cost and power must be non-negative; accuracy must be greater than 0 and at most 100. Unknown effect names are ignored and reported back to the user.

**Example**
```text
/create_move Slash 10 atk 30 95
```

### `/delete_move` (GM)

Remove a move from the currently selected fighter.

**Example**
```text
/delete_move Slash
```

### `/battle_effects`

Display the complete list of effect identifiers accepted by the battle system.

**Example**
```text
/battle_effects
```

### How a move is defined

| Field | How to use it |
|-------|----------------|
| MoveName | A unique move name within the fighter. The implementation stores it in lowercase. |
| ManaCost | Mana consumed immediately when the move is successfully selected. |
| MovesType | `atk` uses ATK against the target DEF. `spa` uses SPA against the target SPD. |
| Power | Base move power used in the damage or healing calculation. |
| Accuracy | Percentage from 1 to 100. The move can miss before damage or effects are applied. |
| Effects | One or more identifiers from `/battle_effects`. Invalid names are ignored. |

### Example move recipes

- **Basic attack:** `/create_move Slash 8 atk 30 95`
- **Special attack:** `/create_move Fireball 12 spa 35 90 burn`
- **Self buff:** `/create_move Focus 6 atk 0 100 atkraise`
- **Multi-target attack:** `/create_move Volley 15 atk 20 85 atkall`
- **Multi-shot attack:** `/create_move Barrage 18 atk 15 80 multishot`

---

## 4. Items and the Battle Bag

Items are separate YAML definitions stored in the battle-system item storage. A player uses an item from their battle bag as one battle action, just like choosing a move.

### Item commands

### `/create_item <ItemName> <Effect> [Value]` (GM)

Create a new item definition. The optional `Value` becomes required for healing, mana restoration, and stat-changing effects. For all other effects, `Value` is omitted.

**Example**
```text
/create_item Potion heal 50
```

### `/give_item <Target_ID> <ItemName> <Quantity>` (GM)

Give item copies to a target player. The item must already exist in item storage, and the target must have a selected fighter.

**Example**
```text
/give_item 42 Potion 3
```

### `/remove_item <Target_ID> <ItemName> <Quantity>` (GM)

Remove the requested number of copies from a target player. The command fails when the target does not have enough copies.

**Example**
```text
/remove_item 42 Potion 1
```

### `/empty_bag <Target_ID>` (GM)

Remove every item from a target player's battle bag.

**Example**
```text
/empty_bag 42
```

### `/bag [Target_ID]`

Show your own item bag. A GM can provide `Target_ID` to inspect another player's bag. The target must have a selected fighter. Multiple copies are grouped by item name.

**Examples**
```text
/bag
/bag 42
```

### `/use_item <ItemName> [Target_ID]`

Select an item for the current battle turn. An item uses the player's turn, costs no mana, and is consumed when the action resolves. A `Target_ID` is required for ordinary single-target items; an item carrying `atkall` can omit the target.

**Example**
```text
/use_item Potion 42
```

### Bag behavior

- The bag stores copies by item name; giving 3 Potions creates three usable copies.
- Selecting an item does not immediately remove it from the bag.
- The selected item is consumed when its action is resolved, after stun/confusion/sleep/paralysis checks.
- Battle refreshes and fighter reloads preserve the player's bag contents.

---

## 5. Item Definitions and Value Rules

A typical item YAML contains a name and an effect. `Value` is added only for effects that use it.

```text
Name: potion
Effect: heal
Value: 50.0
```

```text
Name: power_charm
Effect: atkraise
Value: 1.5
```

```text
Name: mana_capsule
Effect: manarestore
Value: 30.0
```

### Value rules

| Effect category | Value behavior |
|------------------|----------------|
| heal | Absolute amount of HP restored, capped at max HP. |
| manarestore | Absolute amount of mana restored to the selected target. |
| Self stat raises | Explicit multiplier applied to the selected fighter stat. |
| Target stat decreases | Explicit divisor applied to the target stat. |
| Ally stat raises | Explicit multiplier applied to the ally stat. |
| Other effects | Value is omitted and ignored. |

### No direct damage field

Items do not have move-type, power, or accuracy fields. Therefore, an item does not perform direct attack damage. Effects such as poison, burn, freeze, status changes, buffs, debuffs, steals, and healing are resolved through the same effect helpers used by the battle engine.

### Mana restoration

`manarestore` restores a fixed amount of mana specified by `Value`. It is treated as an ally/support effect, so it can be used on yourself or another eligible ally.

---

## 6. Joining and Playing a Battle

### `/fight`

Join the active battle, or reconnect to a previously occupied fighter slot after a disconnect. You must have a selected fighter and be in an area where battles are allowed.

**Example**
```text
/fight
```

### `/battle_info`

Display the current battle roster. Fighters are grouped by guild where applicable, and a HP percentage is shown when the area setting `show_hp` is enabled.

**Example**
```text
/battle_info
```

### `/use_move [Target_ID]`

Select a move for the current turn. Use the move name or the numeric ID shown by `/info_fighter`. A target is required for ordinary single-target moves; an `atkall` move can omit the target.

**Example**
```text
/use_move 0 42
```

### `/use_item [Target_ID]`

Select an item for the current turn. Use the item name. A target is required for ordinary single-target items; an `atkall` item can omit the target.

**Example**
```text
/use_item Potion 42
```

### `/skip_move`

Skip the current turn. The turn resolves when every active fighter has selected an action.

**Example**
```text
/skip_move
```

### `/surrender`

Leave the battle voluntarily. If you have not selected an action, you are removed immediately; otherwise your fighter is treated as defeated before being reset.

**Example**
```text
/surrender
```

### Turn sequence

1. Players select a move, an item, or skip.
2. When everyone has selected an action, the fighters are sorted by SPE, fastest first.
3. Each selected action is resolved in that order.
4. End-of-turn poison, burn, and freeze damage is applied.
5. Defeated fighters are removed and their fighter state is reset from the stored definition.
6. If only one fighter remains, that fighter wins. A surviving guild can also win when all remaining fighters belong to the same guild.

### Targeting tips

Use `/battle_info` to identify the numeric client ID of the fighter you want to target. Guild membership affects area-of-effect ally/enemy targeting for actions carrying `atkall`.

---

## 7. Battle Effects Reference

The following descriptions are based on the current effect-handling code. Some effects are meaningful mainly because they are paired with a move type or another effect. All item effects listed here are accepted by `/create_item`.

| Effect | Behavior |
|--------|----------|
| atkraise | Raise the user's ATK. |
| sparaise | Raise the user's SPA. |
| defraise | Raise the user's DEF. |
| spdraise | Raise the user's SPD. |
| speraise | Raise the user's SPE. |
| atkdown | Lower the target's ATK. |
| defdown | Lower the target's DEF. |
| spadown | Lower the target's SPA. |
| spddown | Lower the target's SPD. |
| spedown | Lower the target's SPE. |
| heal | Heal a target. Healing is capped at max HP. |
| manarestore | Restore a fixed amount of mana to the target. Items use their `Value` amount. |
| healstatus | Remove the target's current status. Removing burn also restores the defensive stats reduced by burn. |
| poison | Apply poison if the target has no current status. |
| paralysis | Apply paralysis if the target has no current status. |
| burn | Apply burn if the target has no current status and reduce SPD and DEF. |
| freeze | Apply freeze if the target has no current status; freeze also deals end-of-turn damage. |
| stunned | Apply stunned if the target has no current status; the next action is lost. |
| confused | Apply confusion if the target has no current status; future turns use the area confusion rate. |
| sleep | Apply a sleep sequence. Sleeping fighters lose turns before waking. |
| enraged | Store an enraged status on the user; the next successful attack uses the area enraged multiplier. |
| atkall | Make the action area-targeted. For enemy actions it targets opponents; for ally/support actions it targets allies in the user's guild, or all fighters if unguilded. |
| atkraiseally | Raise an ally's ATK. |
| defraiseally | Raise an ally's DEF. |
| sparaiseally | Raise an ally's SPA. |
| spdraiseally | Raise an ally's SPD. |
| speraiseally | Raise an ally's SPE. |
| stealatk | Transfer part of the target's ATK to the user. |
| burn / freeze / status effects | Apply the corresponding status behavior described above. |

---

## 8. Item Effect List

These are the effect identifiers accepted by `/create_item`. The item system intentionally has its own accepted list.

| Effect | Uses Value? |
|--------|-------------|
| atkraise | Yes — multiplier |
| sparaise | Yes — multiplier |
| defraise | Yes — multiplier |
| spdraise | Yes — multiplier |
| speraise | Yes — multiplier |
| atkdown | Yes — divisor |
| defdown | Yes — divisor |
| spadown | Yes — divisor |
| spddown | Yes — divisor |
| spedown | Yes — divisor |
| heal | Yes — HP amount |
| manarestore | Yes — mana amount |
| atkraiseally | Yes — multiplier |
| defraiseally | Yes — multiplier |
| sparaiseally | Yes — multiplier |
| spdraiseally | Yes — multiplier |
| speraiseally | Yes — multiplier |
| poison | No |
| paralysis | No |
| atkall | No |
| stealatk | No |
| burn | No |
| freeze | No |
| stunned | No |
| confused | No |
| enraged | No |
| sleep | No |
| healstatus | No |

### Important

The item list contains `stealatk` but does not add the other steal effects used by moves. Likewise, items do not use move power/type/accuracy fields.

---

## 9. Guilds

### `/create_guild`

Create a guild. The creator automatically becomes the first member and therefore the guild leader.

**Example**
```text
/create_guild Guardians
```

### `/info_guild`

Display the current guild, its leader, and its members.

**Example**
```text
/info_guild
```

### `/join_guild`

Used by the guild leader to invite a fighter into the guild. The target must have a selected fighter and must not already belong to a guild.

**Example**
```text
/join_guild 42
```

### `/leave_guild [Target_ID]`

Leave your current guild with no argument. A GM/area owner can remove a target, and the guild leader can remove another member.

**Examples**
```text
/leave_guild
/leave_guild 42
```

### `/close_guild [GuildName]` (GM)

Close every guild when no name is supplied, or close one named guild. Guild references on members are cleared when all guilds are closed; closing one guild removes that guild from the guild registry.

**Example**
```text
/close_guild Guardians
```

### Guild leader rule

The first client in the guild member list is treated as the guild leader. The `/join_guild` command checks against that first member.

---

## 10. GM and Battle Administration

### `/battle_config` (GM)

Change battle settings for the current area. Running `/battle_config` without a parameter lists the accepted parameter names.

**Example**
```text
/battle_config critical_rate 20
```

### `/refresh_battle` (GM)

Reset the current battle lobby: selected actions and targets are cleared, the fighter list is emptied, and the battle is marked as not started. Fighter temporary battle state is restored from the stored definitions.

**Example**
```text
/refresh_battle
```

### `/remove_fighter` (GM)

Force a fighter to leave. A fighter that has already selected an action is treated as defeated; otherwise it is simply removed from the active fighter list.

**Example**
```text
/remove_fighter 42
```

### `/force_skip_move` (GM)

Force a fighter to skip the current turn. This counts as that fighter having selected an action.

**Example**
```text
/force_skip_move 42
```

### Battle configuration parameters

| Parameter | Purpose |
|-----------|---------|
| paralysis_rate | Controls the random paralysis skip check. |
| critical_rate | Controls the random critical-hit check. |
| critical_bonus | Multiplier applied to critical damage. |
| bonus_malus | Multiplier used by normal stat buffs and debuffs. |
| poison_damage | End-of-turn poison damage is max HP divided by this value. |
| show_hp | `true` / `false`. Shows or hides HP percentage in battle information. |
| min_multishot | Minimum number of shots for multishot. |
| max_multishot | Maximum number of shots for multishot. |
| burn_damage | End-of-turn burn damage is max HP divided by this value. |
| freeze_damage | End-of-turn freeze damage is max HP divided by this value. |
| confusion_rate | Controls the confusion random roll. |
| enraged_bonus | Damage multiplier consumed by the next successful attack while enraged. |
| stolen_stat | Divisor used to determine how much of a target stat is transferred by steal effects. |

### Configuration validation

The current implementation rejects a multishot configuration where `min_multishot` is greater than `max_multishot`. The parameter is spelled `show_hp`, not `"show hp"`.

---

## 11. Practical Example: Using an Item in a Round

Imagine two fighters are already in the battle. Fighter A owns item `Potion`, defined as `heal` with `Value` 50. Fighter B has client ID `42`.

**Step 1 — Check your fighter, available moves, and item bag:**
```text
/info_fighter
```

You can also inspect only the bag with:
```text
/bag
```

**Step 2 — Check the battle roster and target IDs:**
```text
/battle_info
```

**Step 3 — Select the item:**
```text
/use_item Potion 42
```

**Step 4 —** The opponent selects their action. When every active fighter has selected an action, the turn starts automatically.

**Step 5 —** Actions resolve from highest SPE to lowest SPE. The item consumes one Potion only when its action is resolved, then applies its effect to the selected target.

**Step 6 —** Use `/battle_info` and `/info_fighter` after the round to inspect the new state.

### Example: mana restoration

```text
/create_item ManaCapsule manarestore 30
/use_item ManaCapsule 42
```

The same item can target yourself or an eligible ally by using the corresponding client ID. The restored amount is the item's `Value`.

---

## 12. Common Troubleshooting

| Message | What to do |
|---------|------------|
| "You have to choose a fighter first!" | Run `/choose_fighter` before entering battle or creating a move. |
| "You are not ready to fight!" | Run `/fight` before selecting a move or item. |
| "There is no move with that ID!" | Re-run `/info_fighter` and use the numeric move ID shown there. |
| "Your target is not in the fighter list" | Re-run `/battle_info`; the target must currently be an active fighter. |
| "Not enough argument to attack" | Supply a `Target_ID` unless the move/item is configured with `atkall`. |
| "You don't have enough mana" | Pick a cheaper move or restore/reset the fighter state. |
| "You don't have this item in your bag!" | Ask a GM to give the item with `/give_item`. |
| "This item no longer exists in the item storage." | The item definition was removed or renamed; contact a GM. |
| "This item has an invalid Value." | The item definition needs a positive `Value` for heal, mana restoration, or stat-changing effects. |
| "Target does not have enough [item]" | Reduce the quantity or give the target more copies first. |

### Targeting reminder

Ordinary single-target actions require a `Target_ID`. Actions carrying `atkall` can omit the target and resolve against their area-defined target group. For items, `atkall` only changes targeting; because items have no direct power/type fields, a standalone `atkall` item has no direct damage.

---

## 13. Command Cheat Sheet

| Command | Typical permission |
|---------|---------------------|
| `/choose_fighter` | Player |
| `/info_fighter` | Player |
| `/create_fighter <...>` | GM |
| `/create_move <...>` | Player / builder |
| `/create_item <...>` | GM |
| `/give_item <...>` | GM |
| `/remove_item <...>` | GM |
| `/empty_bag` | GM |
| `/bag [Target_ID]` | Player / GM for target view |
| `/use_item [Target_ID]` | Player |
| `/modify_stat <...>` | GM |
| `/delete_fighter` | GM |
| `/delete_move` | GM |
| `/battle_config` | GM |
| `/fight` | Player |
| `/use_move [Target_ID]` | Player |
| `/battle_info` | Player |
| `/refresh_battle` | GM |
| `/remove_fighter` | GM |
| `/surrender` | Player |
| `/skip_move` | Player |
| `/force_skip_move` | GM |
| `/create_guild` | Player |
| `/info_guild` | Player |
| `/join_guild` | Guild leader |
| `/leave_guild [Target_ID]` | Player / leader / GM |
| `/close_guild [GuildName]` | GM |
| `/battle_effects` | Player |

### Item quick reference

- **Create:** `/create_item ItemName Effect [Value]`
- **Give:** `/give_item Target_ID ItemName Quantity`
- **Bag:** `/bag [Target_ID]`
- **Use:** `/use_item ItemName [Target_ID]`

Players can view their own bag; GM target inspection uses `Target_ID`. Items use one full turn, cost no mana, and are consumed when their action resolves.

---

*This guide focuses on the command interface. It intentionally does not define game balance values beyond what can be inferred from the current implementation and configuration parameters.*
