import React, { useEffect, useState } from "react";
import api, { formatApiError } from "../lib/api";
import { toast } from "sonner";
import { Pause, Play, SkipForward, ExternalLink, Gift, LogOut } from "lucide-react";
import { useAuth } from "../lib/contexts";
import { useNavigate, Link } from "react-