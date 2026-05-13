"""Pydantic models — request/response schemas mirroring MongoDB documents.

Note: MongoDB ObjectId is converted to string for all API responses.
"""
from datetime import datetime
from typing import Optional, List, Literal
from pydantic import BaseModel, EmailStr, Field


# ---------- Project ----------
class ProjectBase(BaseModel):
    title: str
    slug: str
    description: str
    board: str
    difficulty: Literal["INTERMEDIATE", "ADV. INTERMEDIATE"]
    cycleMonth: int = Field(ge=1, le=12)
    cycleYear: int = Field(ge=2024, le=2100)
    stockCount: int = 0
    isActive: bool = False
    githubUrl: Optional[str] = None
    guideUrl: Optional[str] = None
    imageUrl: Optional[str] = None
    componentsPreview: List[str] = Field(default_factory=list)
    guideContent: Optional[str] = None  # markdown body for project detail page
    youtubeUrl: Optional[str] = None


class ProjectCreate(ProjectBase):
    pass


class ProjectOut(ProjectBase):
    id: str
    createdAt: datetime


# ---------- VoteCycle / Vote ----------
class VoteCycleBase(BaseModel):
    cycleMonth: int
    cycleYear: int
    candidateProjectIds: List[str]
    winnerId: Optional[str] = None
    votingOpenAt: datetime
    votingCloseAt: datetime


class VoteCycleOut(VoteCycleBase):
    id: str
    candidates: List[ProjectOut] = []
    totalVotes: int = 0
    results: dict = Field(default_factory=dict)  # candidateId -> count


class VoteSubmit(BaseModel):
    candidateProjectId: str


# ---------- Substitution ----------
class SubstitutionCreate(BaseModel):
    originalProjectId: str
    substitutedProjectId: str


class SubstitutionOut(BaseModel):
    id: str
    userId: str
    originalProjectId: str
    substitutedProjectId: str
    cycleMonth: int
    cycleYear: int
    status: str
    requestedAt: datetime


# ---------- Gift ----------
class GiftCreate(BaseModel):
    """Created via webhook from Shopify order, not directly."""
    buyerShopifyOrderId: str
    recipientEmail: EmailStr
    durationMonths: Literal[1, 3]


class GiftRedeem(BaseModel):
    code: str
    shippingAddressShopifyCustomerId: Optional[str] = None


class GiftOut(BaseModel):
    id: str
    code: str
    recipientEmail: str
    durationMonths: int
    status: str
    createdAt: datetime


# ---------- Waitlist ----------
class WaitlistJoin(BaseModel):
    email: EmailStr
    name: str = Field(min_length=1, max_length=120)
    source: Optional[str] = "home_hero"
    ref: Optional[str] = None  # referral code of the inviter, if any
    ref_src: Optional[str] = Field(default=None, max_length=16)  # platform attribution: tw, bsky, wa, sms, email, native, etc.


class WaitlistStatus(BaseModel):
    code: str
    email: str
    name: str
    waitlistReferrals: int        # how many waitlist signups used this code
    paidReferrals: int            # how many of those have since paid (after launch)
    priority: bool                # waitlistReferrals >= 3
    freeMonthEarned: bool         # paidReferrals >= 5 AND this user is themselves active
    selfActive: bool              # true if this user is now a paid subscriber
    createdAt: datetime


# ---------- User / Subscription ----------
class SubscriptionStatusOut(BaseModel):
    status: str
    nextBillingDate: Optional[datetime] = None
    contractId: Optional[str] = None
    voteEligibleCycles: List[str] = []
    canVote: bool = False


class SubscriptionAction(BaseModel):
    action: Literal["pause", "resume", "skip"]


# ---------- Admin ----------
class AdminProjectActivate(BaseModel):
    projectId: str


# ---------- Helpers ----------
def serialize(doc: dict) -> dict:
    """Strip MongoDB _id and convert to string id."""
    if not doc:
        return doc
    out = {k: v for k, v in doc.items() if k != "_id"}
    if "_id" in doc:
        out["id"] = str(doc["_id"])
    # Coerce nested ObjectIds
    for k, v in out.items():
        if hasattr(v, "binary"):  # bson.ObjectId
            out[k] = str(v)
    return out
