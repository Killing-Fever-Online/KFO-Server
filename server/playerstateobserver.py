class PlayerStateObserver:
    """
    Keeps the client side player list in sync with the AO 2.11 packets.

    Registration:
        PR#<player_id: int>#<update_type: int>#%
    Player data:
        PU#<player_id: int>#<data_type: int>#<data: string>#%

    Clients older than 2.11 drop both packets, so they are sent unconditionally.

    The desired player list is always derived from the live hub/client objects.
    The only state kept is ``client.player_list_ids``, the IDs already sent to
    that particular client via PR ADD. PR ADD appends on the client, so it must
    not be repeated for an ID the client already has.
    """

    ADD = 0
    REMOVE = 1

    NAME = 0
    CHARACTER = 1
    CHARACTER_NAME = 2
    AREA_ID = 3
    DESC = 4
    FORMAT = 5
    COMMANDS = 6

    def __init__(self, server):
        self.server = server
        self.format = "[{id}] {displayname}: {username}"

    def _recipients(self, hub):
        """Clients in the hub that completed joining and receive PR/PU."""
        return [c for c in hub.clients if c.joined]

    def _allowed(self, viewer):
        """Mods/GMs role"""
        return viewer.is_mod or viewer in viewer.area.owners

    def _is_listed_for(self, viewer, client):
        """Whether the client should be listed for the viewer right now."""
        if not (client.joined and client.area is not None):
            return False
        if client.area.area_manager is not viewer.area.area_manager:
            return False
        # We always see our own state
        if viewer == client:
            return True

        same_area = client.area is viewer.area

        # (same area OR the hub allows seeing areas) AND the viewer is allowed
        if (
            (same_area or viewer.area.area_manager.can_getareas)
            and self._allowed(viewer)
        ):
            return True

        # Otherwise the client's area must be visible and the client not hidden
        return (
            client.area.can_getarea
            and not client.area.dark
            and not client.hidden
            and not viewer.blinded
        )

    def _desired_ids(self, viewer):
        """IDs the viewer should currently have on its player list."""
        return {
            c.id for c in self._recipients(viewer.area.area_manager)
            if self._is_listed_for(viewer, c)
        }

    def _sync_player(self, viewer, client):
        """Add, update or remove one player in one viewer's list."""
        desired = self._is_listed_for(viewer, client)
        present = client.id in viewer.player_list_ids

        if desired and not present:
            self.send_player_state(viewer, client)
            viewer.player_list_ids.add(client.id)
        elif desired and present:
            self.update_player_state(viewer, client)
        elif not desired and present:
            viewer.send_command("PR", client.id, self.REMOVE)
            viewer.player_list_ids.discard(client.id)

    def _sync_viewer(self, viewer):
        """Reconcile the viewer's whole list against the live hub state."""
        desired = self._desired_ids(viewer)

        for player_id in viewer.player_list_ids - desired:
            viewer.send_command("PR", player_id, self.REMOVE)
        viewer.player_list_ids.intersection_update(desired)

        for other in self._recipients(viewer.area.area_manager):
            if other.id not in desired:
                continue
            if other.id in viewer.player_list_ids:
                # The viewer already has this row; only refresh its commands.
                if other is not viewer:
                    self.update_player_state(viewer, other)
            else:
                self.send_player_state(viewer, other)
                viewer.player_list_ids.add(other.id)

    def refresh_hub(self, hub):
        """Reconcile every viewer, sending packets only for changed entries."""
        for viewer in self._recipients(hub):
            self._sync_viewer(viewer)

    def _clear_player_list(self, viewer):
        """Forget everything the viewer has listed, removing each row."""
        for player_id in list(viewer.player_list_ids):
            viewer.send_command("PR", player_id, self.REMOVE)
        viewer.player_list_ids.clear()

    def send_player_state(self, target, client):
        """Send every field of a single player to one target."""
        target.send_command("PR", client.id, self.ADD)
        self.update_player_state(target, client)

    def update_player_state(self, target, client):
        target.send_command("PU", client.id, self.NAME, client.name)
        target.send_command("PU", client.id, self.CHARACTER, client.f_char_name)
        target.send_command("PU", client.id,
                            self.CHARACTER_NAME, client.showname)
        target.send_command("PU", client.id, self.AREA_ID,
                            self.get_area_id(target, client))
        desc = client.desc
        if client.iniswap != "":
            desc = f"[Char Folder: {client.char_name}]\n{desc}"
        target.send_command("PU", client.id, self.DESC, desc)
        format = self.format
        info = ""
        if client in client.area.afkers:
            info += "💤"
        if client.hidden:
            name = ""
            if client.hidden_in is not None:
                name = f":{client.area.evi_list.evidences[client.hidden_in].name}"
            info += f"📦{name}"
        elif (target == client or self._allowed(target)) and client.sneaking:
            info += f"🥷"
        if client.is_mod:
            info += "[M]"
        elif client in target.area.area_manager.owners:
            info += "[GM]"
        elif client in target.area._owners:
            info += "[CM]"
        if info != "":
            format = f"{info}{format}"
        if target.following == client:
            format += " 👣"
        target.send_command("PU", client.id, self.FORMAT, format)
        self.send_command_list(target, client)

    def send_command_list(self, target, client):
        # list of command actions the server lets you do on the player
        # format: Action Name{}ooc message to send
        # {} is a delimiter where the stuff behfore it is the action name
        # {id} replaces with player id
        # {character} replaces with character folder
        # {displayname} replaces with showname
        # {username} replaces with username
        # {desc} replaces with description
        command_list = []
        if target != client:
            if target.following == client:
                command_list.append("Unfollow{}/unfollow")
            else:
                command_list.append("Follow{}/follow {id}")
        else:
            command_list.append("Unfollow Others{}/unfollow")
            if target.sneaking:
                command_list.append("Unsneak{}/unsneak")
            else:
                command_list.append("Sneak{}/sneak")
        command_list.append("Cast a Vote{}/vote {id}")
        command_list.append("Check Description{}/chardesc {id}")
        # is CM, give CM commands
        if target in target.area.owners:
            if client.id in target.area.invite_list:
                command_list.append("Uninvite from Speaking{}/uninvite {id}")
            else:
                command_list.append("Invite to Speak{}/invite {id}")
            if not client.char_id == -1:
                command_list.append("Kill w/ Corpse{}/kill {id} 1")
                command_list.append("Kill (Disappear){}/kill {id} 0")
            if client.frozen:
                command_list.append("Unfreeze{}/unfreeze {id}")
            else:
                command_list.append("Freeze{}/freeze {id}")

        # is GM, give GM commands
        if target in target.area.area_manager.owners:
            if client.blinded:
                command_list.append("Unblind{}/unblind {id}")
            else:
                command_list.append("Blind{}/blind {id}")
            if client.deafened:
                command_list.append("Undeafen{}/undeafen {id}")
            else:
                command_list.append("Deafen{}/deafen {id}")
            if client.player_muted:
                command_list.append("Unmute{}/player_unmute {id}")
            else:
                command_list.append("Mute{}/player_mute {id}")
            if client.forced_blankpost:
                command_list.append("Unforce Blankpost{}/unforce_blankpost {id}")
            else:
                command_list.append("Force Blankpost{}/force_blankpost {id}")
            if client.hidden:
                command_list.append("Unhide{}/player_unhide {id}")
            else:
                command_list.append("Hide{}/player_hide {id}")
            if client.sneaking:
                command_list.append("Unsneak{}/unsneak {id}")
            else:
                command_list.append("Sneak{}/sneak {id}")

        target.send_command("PU", client.id, self.COMMANDS, '&'.join(command_list))

    def get_area_id(self, target, client):
        """
        Get the index the client's area sits at in the target's own area list.
        Every client gets its own area list, so this cannot be broadcast as one
        value the way the other player data can.
        """
        try:
            area_id = target.local_area_list.index(client.area)
        except ValueError:
            return -1
        # The hub entry takes up the first slot of the area list.
        if len(self.server.hub_manager.hubs) > 1:
            area_id = area_id + 1
        return area_id

    def notify_changed(self, client, old_hub=None):
        """Re-send the client's state everywhere it is relevant."""
        if not client.joined:
            return
        hub = client.area.area_manager

        if old_hub is not None and old_hub is not hub:
            # Drop the client from old-hub viewers.
            for viewer in self._recipients(old_hub):
                if client.id in viewer.player_list_ids:
                    viewer.send_command("PR", client.id, self.REMOVE)
                    viewer.player_list_ids.discard(client.id)
            # Clear the moving client's old-hub view.
            self._clear_player_list(client)

        # Update this client's row for every other viewer.
        for viewer in self._recipients(hub):
            if viewer is not client:
                self._sync_player(viewer, client)

        # Refresh the client's own row and reconcile its whole view.
        self._sync_player(client, client)
        self._sync_viewer(client)
