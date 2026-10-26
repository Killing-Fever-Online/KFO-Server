class PlayerStateObserver:
    """
    Keeps the client side player list in sync with the AO 2.11 packets.

    Registration:
        PR#<player_id: int>#<update_type: int>#%
    Player data:
        PU#<player_id: int>#<data_type: int>#<data: string>#%

    Clients older than 2.11 drop both packets, so they are sent unconditionally.
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
        # Clients that receive player list packets.
        self.client_list = []
        # Clients that are currently listed for everyone else.
        self.listed = set()
        # The format to use
        self.format = "[{id}] {displayname} {username}"

    def register_client(self, client):
        """Hand the client the player list, then announce it to everyone else."""
        if client in self.client_list:
            return
        self.client_list.append(client)
        self.send_player_list(client)
        self.notify_visibility_changed(client)

    def unregister_client(self, client):
        """Drop the client from the player list of everyone still connected."""
        if client not in self.client_list:
            return
        self.client_list.remove(client)
        if client in self.listed:
            self.listed.discard(client)
            self.send_to_client_list(client, "PR", client.id, self.REMOVE)

    def send_player_list(self, client, exclude_self = False):
        """Send every listed player of the client's hub to that client."""
        for other in self.client_list:
            if exclude_self and other is client:
                continue
            if other not in self.listed:
                continue
            if other.area.area_manager != client.area.area_manager:
                continue
            self.send_player_state(client, other)

    def send_player_state(self, target, client):
        """Send every field of a single player to one target."""
        target.send_command("PR", client.id, self.ADD)
        self.update_player_state(target, client)

    def update_player_state(self, target, client):
        target.send_command("PU", client.id, self.NAME, client.name)
        target.send_command("PU", client.id, self.CHARACTER, client.char_name)
        target.send_command("PU", client.id,
                            self.CHARACTER_NAME, client.showname)
        target.send_command("PU", client.id, self.AREA_ID,
                            self.get_area_id(target, client))
        target.send_command("PU", client.id, self.DESC, client.desc)
        target.send_command("PU", client.id, self.FORMAT, self.format)

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
                command_list.append("Unfollow Player{}/unfollow")
            else:
                command_list.append("Follow Player{}/follow {id}")
        else:
            command_list.append("Unfollow Others{}/unfollow")
            if target.sneaking:
                command_list.append("Unsneak{}/unsneak")
            else:
                command_list.append("Sneak{}/sneak")
        command_list.extend([
            "Vote for Player{}/vote {id}",
            "Check Description{}/chardesc {id}"
        ])
        # is CM, give CM commands
        if target in target.area.owners:
            if client.id in target.area.invite_list:
                command_list.append("Uninvite Player from Speaking{}/uninvite {id}")
            else:
                command_list.append("Invite Player to Speak{}/invite {id}")
            if not client.char_id == -1:
                command_list.append("Kill Player{}/kill {id}")
            if client.frozen:
                command_list.append("Unfreeze Player{}/unfreeze {id}")
            else:
                command_list.append("Freeze Player{}/freeze {id}")
            
        # is GM, give GM commands
        if target in target.area.area_manager.owners:
            if client.blinded:
                command_list.append("Unblind Player{}/unblind {id}")
            else:
                command_list.append("Blind Player{}/blind {id}")
            if client.deafened:
                command_list.append("Undeafen Player{}/undeafen {id}")
            else:
                command_list.append("Deafen Player{}/deafen {id}")
            if client.player_muted:
                command_list.append("Unmute Player{}/player_unmute {id}")
            else:
                command_list.append("Mute Player{}/player_mute {id}")
            if client.forced_blankpost:
                command_list.append("Unforce Blankpost from Player{}/unforce_blankpost {id}")
            else:
                command_list.append("Force Blankpost for Player{}/force_blankpost {id}")
            if client.hidden:
                command_list.append("Unhide Player{}/player_unhide {id}")
            else:
                command_list.append("Hide Player{}/player_hide {id}")
            if client.sneaking:
                command_list.append("Unsneak Player{}/unsneak {id}")
            else:
                command_list.append("Sneak Player{}/sneak {id}")

        print(f"Sending player state to [{target.id}] {target.showname} for [{client.id}] {client.showname}...")
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

    def send_to_client_list(self, client, command, *args):
        """Send a packet about the client to every player list of its hub."""
        for target in self.client_list:
            if target.area.area_manager != client.area.area_manager:
                continue
            target.send_command(command, *args)

    def notify_name_changed(self, client):
        if client not in self.listed:
            return
        self.send_to_client_list(
            client, "PU", client.id, self.NAME, client.name)

    def notify_character_changed(self, client):
        """
        Announce a character change. Picking a character also takes the client
        out of spectator, so the listing itself may have to be added or dropped.
        """
        if client not in self.listed or client.hidden:
            self.notify_visibility_changed(client)
            return
        self.send_to_client_list(
            client, "PU", client.id, self.CHARACTER, client.char_name)
        self.send_to_client_list(
            client, "PU", client.id, self.CHARACTER_NAME, client.showname)

    def notify_character_name_changed(self, client):
        if client not in self.listed:
            return
        self.send_to_client_list(
            client, "PU", client.id, self.CHARACTER_NAME, client.showname)

    def notify_area_id_changed(self, client):
        if client not in self.listed:
            return
        for target in self.client_list:
            if target.area.area_manager != client.area.area_manager:
                continue
            target.send_command("PU", client.id, self.AREA_ID,
                                self.get_area_id(target, client))

    def notify_visibility_changed(self, client):
        """Add or drop the listing of a client that hid or revealed itself."""
        if client not in self.client_list:
            return
        if client.hidden:
            if client in self.listed:
                self.listed.discard(client)
                self.send_to_client_list(
                    client, "PR", client.id, self.REMOVE)
            return
        if client in self.listed:
            return
        self.listed.add(client)
        for target in self.client_list:
            if target.area.area_manager != client.area.area_manager:
                continue
            self.send_player_state(target, client)

    def notify_hub_changed(self, client, old_hub):
        """Move the client's listing over to the hub it just joined."""
        if client not in self.client_list:
            return
        client.send_command("PR", client.id, self.REMOVE)
        for other in self.client_list:
            if other is not client and other.area.area_manager == old_hub:
                client.send_command("PR", other.id, self.REMOVE)
        if client in self.listed:
            self.listed.discard(client)
            for target in self.client_list:
                if target is not client and target.area.area_manager == old_hub:
                    target.send_command("PR", client.id, self.REMOVE)
        self.send_player_list(client)


    def notify_changed(self, client):
        """Notify a general change"""
        print(f"NOTIFY CHANGED CALLED ON [{client.id}] {client.showname}")
        for other in self.client_list:
            self.update_player_state(other, client)
            self.update_player_state(client, other)
        # self.notify_visibility_changed(client)
