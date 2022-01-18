# Raffle Contract - Example for illustrative purposes only.

import smartpy as sp


class Raffle(sp.Contract):
    def __init__(self, address):
        self.init(admin=address,
                  close_date=sp.timestamp(0),
                  jackpot=sp.tez(0),
                  raffle_is_open=False,
                  players=sp.set(),
                  sold_tickets=sp.map(),
                  hash_winning_ticket=sp.bytes('0x')
                  )

    @sp.entry_point
    def open_raffle(self, jackpot_amount, close_date, hash_winning_ticket):
        sp.verify_equal(sp.source, self.data.admin, message="Administrator not recognized.")
        sp.verify(~ self.data.raffle_is_open, message="A raffle is already open.")
        sp.verify(sp.amount >= jackpot_amount, message="The administrator does not own enough tz.")
        today = sp.now
        in_7_day = today.add_days(7)
        sp.verify(close_date > in_7_day, message="The raffle must remain open for at least 7 days.")
        self.data.close_date = close_date
        self.data.jackpot = jackpot_amount
        self.data.hash_winning_ticket = hash_winning_ticket
        self.data.raffle_is_open = True

    @sp.entry_point
    def buy_ticket(self):
        ticket_price = sp.tez(1)
        current_player = sp.sender
        sp.verify(self.data.raffle_is_open, message="The raffle is closed.")
        sp.verify(sp.amount == ticket_price,
                  message="The sender did not send the right tez amount (Ticket price = 1tz).")
        sp.verify(~ self.data.players.contains(current_player), message="Each player can participate only once.")
        self.data.players.add(current_player)
        ticket_id = abs(sp.len(self.data.players) - 1)
        self.data.sold_tickets[ticket_id] = current_player


    @sp.add_test(name="Raffle")
    def test():
        alice = sp.test_account("Alice")
        jack = sp.test_account("Jack")
        admin = sp.test_account("Administrator")

        r = Raffle(admin.address)
        scenario = sp.test_scenario()
        scenario.h1("Raffle")
        scenario += r

        scenario.h2("Test open_raffle entrypoint")
        close_date = sp.timestamp_from_utc_now().add_days(8)
        jackpot_amount = sp.tez(10)
        number_winning_ticket = sp.nat(345)
        bytes_winning_ticket = sp.pack(number_winning_ticket)
        hash_winning_ticket = sp.sha256(bytes_winning_ticket)

        scenario.h3("The unauthorized user Alice unsuccessfully call open_raffle")
        scenario += r.open_raffle(close_date=close_date, jackpot_amount=jackpot_amount,
                                  hash_winning_ticket=hash_winning_ticket) \
            .run(source=alice.address, amount=sp.tez(10), now=sp.timestamp_from_utc_now(),
                 valid=False)

        scenario.h3("Admin unsuccessfully call open_raffle with wrong close_date")
        close_date = sp.timestamp_from_utc_now().add_days(4)
        scenario += r.open_raffle(close_date=close_date, jackpot_amount=jackpot_amount,
                                  hash_winning_ticket=hash_winning_ticket) \
            .run(source=admin.address, amount=sp.tez(10), now=sp.timestamp_from_utc_now(),
                 valid=False)

        scenario.h3("Admin unsuccessfully call open_raffle by sending not enough tez to the contract")
        close_date = sp.timestamp_from_utc_now().add_days(8)
        scenario += r.open_raffle(close_date=close_date, jackpot_amount=jackpot_amount,
                                  hash_winning_ticket=hash_winning_ticket) \
            .run(source=admin.address, amount=sp.tez(5), now=sp.timestamp_from_utc_now(),
                 valid=False)

        scenario.h3("Admin successfully call open_raffle")
        scenario += r.open_raffle(close_date=close_date, jackpot_amount=jackpot_amount,
                                  hash_winning_ticket=hash_winning_ticket) \
            .run(source=admin.address, amount=sp.tez(10), now=sp.timestamp_from_utc_now())
        scenario.verify(r.data.close_date == close_date)
        scenario.verify(r.data.jackpot == jackpot_amount)
        scenario.verify(r.data.raffle_is_open)

        scenario.h3("Admin unsuccessfully call open_raffle because a raffle is already open")
        scenario += r.open_raffle(close_date=close_date, jackpot_amount=jackpot_amount,
                                  hash_winning_ticket=hash_winning_ticket) \
            .run(source=admin.address, amount=sp.tez(10), now=sp.timestamp_from_utc_now(),
                 valid=False)

        scenario.h2("Test buy_ticket entrypoint (at this point a raffle is open)")

        scenario.h3("Alice unsuccessfully call buy_ticket by sending a wrong amount of tez")
        scenario += r.buy_ticket().run(sender=alice.address, amount=sp.tez(3), valid=False)

        scenario.h3("Alice successfully call buy_ticket")
        scenario += r.buy_ticket().run(sender=alice.address, amount=sp.tez(1))
        alice_ticket_id = sp.nat(0)
        scenario.verify(r.data.players.contains(alice.address))
        scenario.verify_equal(r.data.sold_tickets[alice_ticket_id], alice.address)

        scenario.h3("Alice unsuccessfully call buy_ticket because she has already buy one")
        scenario += r.buy_ticket().run(sender=alice.address, amount=sp.tez(1), valid=False)

        scenario.h3("Jack successfully call buy_ticket")
        scenario += r.buy_ticket().run(sender=jack.address, amount=sp.tez(1))
        jack_ticket_id = sp.nat(1)
        scenario.verify(r.data.players.contains(jack.address))
        scenario.verify(r.data.players.contains(alice.address))
        scenario.verify_equal(r.data.sold_tickets[alice_ticket_id], alice.address)
        scenario.verify_equal(r.data.sold_tickets[jack_ticket_id], jack.address)
