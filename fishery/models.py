import math
from . import utils
from otree.api import (
    models, widgets, BaseConstants, BaseSubsession, BaseGroup, BasePlayer,
    Currency
)

author = 'Fan Yuting & Liu Hang'
doc = """Fishery app, etc."""


class Constants(BaseConstants):
    name_in_url = 'fishery'
    players_per_group = None
    num_rounds = 100

    # Sets the parameters, need to be changed accordingly but not:
    para_intrinsic_growth_rate = models.FloatField()
    para_strength_of_density_regulation = models.FloatField()
    para_total_num_of_fish = models.PositiveIntegerField()

    # Views
    instructions_template = 'fishery/Instructions.html'


class Subsession(BaseSubsession):
    # Creates the parameters

    # Record it here since we will need the value for each single year
    num_fish_at_start_of_year = models.IntegerField()
    this_year_yield = models.FloatField()
    this_year_sustainable_yield = models.FloatField()

    # Initializes the average info attributes
    this_year_harvest = models.IntegerField(initial=0)
    total_harvest = models.IntegerField(initial=0)
    numPlayers = models.IntegerField(initial=0)
    this_year_average_yield = models.FloatField(initial=0)
    total_average_yield = models.FloatField(initial=0)

    # Creates critical value attributes
    rate = models.FloatField()
    a = models.FloatField()  # strength of density regulation
    sustainable_yield_critical_value = models.FloatField()

    def creating_session(self):
        self.num_fish_at_start_of_year = self.session.config['starting_fish_count']
        self.session.vars['continue_game'] = True # For ending the game early when there are no more fish
        self.rate = self.session.config['intrinsic_growth_rate']
        self.a = self.session.config['strength_of_density_regulation']
        self.sustainable_yield_critical_value = \
            (-self.a + math.sqrt(pow(self.a, 2) + pow(self.a, 2) * self.rate))/math.pow(self.a, 2)


    # Adds this method to automatically generate the graph result of the game
    def vars_for_admin_report(self):
        payoffs = sorted([p.payoff for p in self.get_players()])
        return {'payoffs': payoffs}


class Group(BaseGroup):

    def set_payoffs(self):
        # Need to decide whether to end game here if there are no more fish
        # Returns boolean: whether to continue the game
        # Using variable names as used in the Beverton-Holt model

        # (h)arvest: H, total number of fish caught in the round
        # fish_of_this_year: number of fish at the start of year
        # (r)ate: r, intrinsic growth rate
        # a: strength of density regulation

        fish_of_this_year = self.subsession.num_fish_at_start_of_year
        rate = self.session.config['intrinsic_growth_rate']
        a = self.session.config['strength_of_density_regulation']

        harvest = self.subsession.this_year_harvest
        total_harvest = self.subsession.total_harvest
        num_of_players = self.subsession.numPlayers
        ave_year = self.subsession.this_year_average_yield
        ave_total = self.subsession.total_average_yield
        critical = self.subsession.sustainable_yield_critical_value

        # initializes values
        harvest = 0
        num_of_players = len(self.get_players())

        for p in self.get_players():
            harvest += p.num_fish_caught_this_year

        # Updates harvest values
        total_harvest += harvest
        ave_year = harvest / num_of_players
        ave_total = total_harvest / (num_of_players * self.subsession.round_number)

        # Applys the formula here
        num_fish_for_next_year = math.floor(((1 + rate) * fish_of_this_year) / (1 + a * fish_of_this_year) - harvest)
        year_yield = harvest

        if num_fish_for_next_year >= critical:
            year_sustainable_yield = ((1 + rate) * critical) / (1 + a * critical) - critical
        else:
            year_sustainable_yield = ((1 + rate) * fish_of_this_year) / (1 + a * fish_of_this_year) - fish_of_this_year

        if num_fish_for_next_year > 0:
            # Stores the result and pass to the next round later
            self.subsession.num_fish_at_start_of_year = num_fish_for_next_year
            self.subsession.this_year_yield = year_yield
            self.subsession.this_year_sustainable_yield = year_sustainable_yield

            self.subsession.this_year_harvest = harvest
            self.subsession.total_harvest = total_harvest
            self.subsession.numPlayers = num_of_players
            self.subsession.this_year_average_yield = ave_year
            self.subsession.total_average_yield = ave_total

        # Stores the result and pass to the next round later
        self.subsession.num_fish_at_start_of_year = num_fish_for_next_year

        if num_fish_for_next_year > 0:
            # Only give payoff if there are positive number of fish left
            for p in self.get_players():
                p.payoff = p.num_fish_caught_this_year

            return True
        else:
            self.session.vars['fish_history'] = utils.catch_fish_history(self.subsession)
            self.session.vars['yield_history'] = utils.catch_yield_history(self.subsession)
            self.session.vars['sustainable_yield_history'] = utils.catch_sustainable_yield_history(self.subsession)
            return False


class Player(BasePlayer):
    # Name may be duplicated, use student id as the key
    user_name = models.CharField()
    student_id = models.CharField()

    # It will be included in a “documentation” file
    # that is available on the “Data Export” page.
    contribution = models.IntegerField(doc="how much fish you have caught")

    # total_fish_caught = 0
    num_fish_caught_this_year = models.PositiveIntegerField(
        choices=[0, 1, 2],
        widget=widgets.RadioSelect()
    )

    def set_payoffs(self):
        self.is_upgrade = False
        numPlayers = self.subsession.get_players().length
