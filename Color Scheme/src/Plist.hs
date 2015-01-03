module Main where

import qualified Text.XML.Plist as Plist
import qualified Text.XML.HXT.Arrow.XmlState.SystemConfig as Config
import qualified System.FilePath as F
import System.Environment

main :: IO ()
main = do
    args <- getArgs
    let filename = if F.isRelative (head args) then head args else "file://" ++ head args
    plist <- Plist.readPlistFromFile [Config.withValidate False, Config.withSubstDTDEntities False] filename
    let s = process plist
    print s

-- Read a Color Scheme and return the basis colors

process :: Plist.PlObject -> (Maybe String, Maybe String)
process plist = (getBackgroundColor plist, getForegroundColor plist)

getBackgroundColor :: Plist.PlObject -> Maybe String
getBackgroundColor = getBaseColor "background"

getForegroundColor :: Plist.PlObject -> Maybe String
getForegroundColor = getBaseColor "foreground"

getBaseColor :: String -> Plist.PlObject -> Maybe String
getBaseColor selector dict = do
    settings <- selectKey "settings" dict
    array <- getPlArray settings
    base <- noScope array
    settings' <- selectKey "settings" base
    s <- selectKey selector settings'
    getPlString s
    where noScope [] = Nothing
          noScope (x:xs) = do
            keys <- plKeys x
            if "scope" `elem` keys
                then noScope xs
                else return x

selectKey :: String -> Plist.PlObject -> Maybe Plist.PlObject
selectKey _ (Plist.PlDict []) = Nothing
selectKey key (Plist.PlDict (x:xs)) = if fst x == key then Just (snd x) else selectKey key (Plist.PlDict xs)
selectKey _ _ = Nothing

getPlArray :: Plist.PlObject -> Maybe [Plist.PlObject]
getPlArray (Plist.PlArray xs) = Just xs
getPlArray _ = Nothing

plKeys :: Plist.PlObject -> Maybe [String]
plKeys (Plist.PlDict xs) = Just . map fst $ xs
plKeys _ = Nothing

getPlString :: Plist.PlObject -> Maybe String
getPlString (Plist.PlString s) = Just s
getPlString _ = Nothing
